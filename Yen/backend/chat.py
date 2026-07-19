from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from env_loader import load_lab_env
from providers import make_provider
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


def json_text(value: Any, *, max_chars: int | None = None) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def trim_history(history: list[dict[str, str]], window: int) -> list[dict[str, str]]:
    if window <= 0:
        return []
    return history[-window * 2:]


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        result = {"error": "unknown_tool", "message": f"No local implementation for {call.name}"}
    else:
        try:
            result = func(**call.args)
        except Exception as exc:
            result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result, "call_id": call.id}


def tool_results_message(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Provider-neutral tool-result turn.

    `content` is a text rendering every provider can read (Gemini has no
    concept of a `tool` role and just treats this as the next user turn).
    `tool_results` additionally carries each result keyed by the vendor call
    id -- OpenAI-family providers (OpenAI/Groq/OpenRouter) translate this into
    the real `role: "tool"` reply messages their API requires; providers that
    don't need it (Gemini) simply ignore the extra key.
    """
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json_text(events, max_chars=24000)}\n\n"
            "Use only these tool results. If the user asked for a digest and the items are ready, "
            "call the formatting tool. Otherwise answer the user directly with cited sources when available."
        ),
        "tool_results": [
            {"tool_call_id": e["call_id"], "content": json_text(e["result"])}
            for e in events if e.get("call_id")
        ],
    }


def assistant_tool_message(response_text: str | None, calls: list[ToolCall]) -> dict[str, Any]:
    call_summary = [{"name": call.name, "args": call.args} for call in calls]
    content = response_text or "I will call the selected tool(s)."
    return {
        "role": "assistant",
        "content": f"{content}\n\nTOOL_CALLS_JSON:\n{json_text(call_summary)}",
        "text": response_text,
        "tool_calls": [
            {"id": call.id, "name": call.name, "args": call.args} for call in calls if call.id
        ],
    }


def run_model_tool_loop(
    *,
    provider: Any,
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    model: str | None,
    max_tool_rounds: int,
) -> dict[str, Any]:
    working_messages = list(messages)
    rounds: list[dict[str, Any]] = []
    all_tool_events: list[dict[str, Any]] = []
    # Anti-loop guard: some models (confirmed live on gpt-4o-mini) get stuck re-issuing tool
    # calls round after round instead of answering. Two variants seen live:
    # 1. Exact same tool+args repeated (e.g. tra_cuu on a pure symptom query -- always empty,
    #    but the model keeps "double-checking").
    # 2. DIFFERENT query wording each round, but the search tool keeps returning the same top
    #    results anyway (e.g. rephrasing "cách đặt lịch khám" three ways in a row) -- the call
    #    signature differs so #1 doesn't catch it, but the model already has everything it's
    #    going to get and just isn't recognizing that. Track both signatures.
    seen_call_signatures: set[tuple[str, str]] = set()
    seen_result_signatures: set[str] = set()

    for round_index in range(1, max_tool_rounds + 1):
        response = provider.complete(working_messages, tools, model=model, temperature=0.1)
        if not response.text and not response.tool_calls:
            # Gemini/qwen occasionally return a genuinely empty candidate (no visible
            # text, no tool call) -- usually transient, so retry once before giving the
            # patient a blank chat bubble.
            print("⚠️  empty model response, retrying once")
            response = provider.complete(working_messages, tools, model=model, temperature=0.1)
        calls = response.tool_calls
        round_record: dict[str, Any] = {
            "round": round_index,
            "assistant_text": response.text,
            "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
            "tool_results": [],
        }

        if not calls:
            rounds.append(round_record)
            fallback_text = (
                "Xin lỗi, mình chưa nhận được phản hồi rõ ràng. Bạn nhắn lại câu hỏi về dịch vụ, "
                "giá khám hoặc triệu chứng vừa rồi giúp mình nhé."
            )
            return {
                "status": "answered",
                "assistant_text": response.text or fallback_text,
                "rounds": rounds,
                "tool_events": all_tool_events,
            }

        working_messages.append(assistant_tool_message(response.text, calls))
        non_clarification_events: list[dict[str, Any]] = []
        repeated_calls = 0
        repeated_results = 0

        for call in calls:
            print(f"🔧 {call.name}({json.dumps(call.args, ensure_ascii=False, sort_keys=True)})")
            signature = (call.name, json.dumps(call.args, ensure_ascii=False, sort_keys=True))
            if signature in seen_call_signatures:
                repeated_calls += 1
            seen_call_signatures.add(signature)
            event = execute_tool_call(call)
            round_record["tool_results"].append(event)
            all_tool_events.append(event)

            result_signature = f"{call.name}:{json.dumps(event.get('result'), ensure_ascii=False, sort_keys=True)}"
            if result_signature in seen_result_signatures:
                repeated_results += 1
            seen_result_signatures.add(result_signature)

            # Detect the clarification/pause tool by its output flag (rename-proof),
            # not by a hard-coded tool name.
            result = event.get("result", {})
            if isinstance(result, dict) and result.get("awaiting_user"):
                question = result.get("question") or call.args.get("question") or "Bạn bổ sung thêm thông tin nhé."
                # response.text thường là đoạn giải thích/xác nhận đầy đủ (vd: đã diễn giải
                # đúng theo hồ sơ bệnh nhân, kèm gợi ý tự chăm sóc) đi trước lệnh gọi tool
                # clarify() — chỉ dùng riêng "question" khi model không trả về đoạn đó.
                assistant_text = response.text.strip() if response.text and response.text.strip() else question
                rounds.append(round_record)
                return {
                    "status": "waiting_for_user",
                    "assistant_text": assistant_text,
                    "rounds": rounds,
                    "tool_events": all_tool_events,
                }

            non_clarification_events.append(event)

        rounds.append(round_record)
        working_messages.append(tool_results_message(non_clarification_events))
        # NOTE: nudges must be sent as a SEPARATE plain message, not appended to the
        # tool_results_message's own "content" field -- confirmed via transcript inspection
        # that _to_wire_messages() (openai_provider.py) silently DISCARDS that field for
        # OpenAI whenever "tool_results" is present (it only forwards each entry's own
        # per-call content into the role:"tool" replies). Every earlier nudge attempt that
        # appended to tool_msg["content"] was therefore a complete no-op on OpenAI -- the
        # model never saw it, which is why identical repeat queries kept sailing through
        # unblocked despite the guard supposedly firing.
        if calls and (repeated_calls == len(calls) or repeated_results == len(calls)):
            # Every call this round exactly repeats an earlier call, OR returned the same
            # results as an earlier call despite different wording -- force a stop instead of
            # burning the remaining rounds on retries that won't surface anything new.
            working_messages.append({
                "role": "user",
                "content": (
                    "LƯU Ý: Các tool trên vừa trả về đúng kết quả y hệt vòng trước (dù query khác "
                    "chữ), sẽ không có kết quả mới nào khác. DỪNG gọi tool ngay, trả lời NGAY bằng "
                    "JSON theo đúng schema dựa trên thông tin đã có."
                ),
            })
        elif round_index >= max_tool_rounds - 1:
            # Not a detected repeat, but running out of rounds regardless -- confirmed live
            # that gpt-4o-mini can burn all remaining rounds on genuinely-different-but-
            # already-sufficient exploratory searches (e.g. re-querying sub-aspects of one
            # topic) and get cut off mid-research with no answer at all. Give it an explicit
            # heads-up before that happens instead of only reacting after the fact.
            working_messages.append({
                "role": "user",
                "content": (
                    "LƯU Ý: Sắp hết lượt gọi tool (chỉ còn tối đa 1 lượt nữa). Nếu thông tin hiện "
                    "có đã đủ để trả lời, DỪNG gọi tool và trả lời NGAY bằng JSON theo đúng schema."
                ),
            })

    return {
        "status": "max_tool_rounds",
        "assistant_text": (
            "Xin lỗi, mình đang gặp khó khăn để tra cứu đủ thông tin cho câu hỏi này. Bạn thử "
            "hỏi lại ngắn gọn hơn hoặc liên hệ tổng đài bệnh viện giúp mình nhé."
        ),
        "rounds": rounds,
        "tool_events": all_tool_events,
    }


def write_transcript(path: Path, transcript: dict[str, Any]) -> None:
    transcript["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Research Agent chat with transcript logging.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini", "groq"], required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", required=True, help="Student-chosen artifact version label, e.g. v0, v1, v2.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=ROOT / "transcripts")
    parser.add_argument("--history-window", type=int, default=5, help="Keep the last N user/assistant pairs in context.")
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    parser.add_argument("--voice", dest="use_voice", action="store_true",
                        help="Bật chế độ giọng nói: dùng STT để nghe đầu vào, đọc kết quả bằng TTS.")
    parser.add_argument("--voice-type", choices=["male", "female"], default="female",
                        help="Giọng đọc TTS (mặc định: female).")
    args = parser.parse_args()

    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(args.tools)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(args.version, args.system_prompt, args.tools)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([
        safe_slug(args.version),
        safe_slug(args.provider),
        timestamp,
    ])
    transcript_path = args.transcripts_dir / f"{transcript_id}.transcript.json"
    transcript: dict[str, Any] = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": args.provider,
        "model": selected_model,
        "system_prompt": str(args.system_prompt),
        "tools": str(args.tools),
        "history_window": args.history_window,
        "max_tool_rounds": args.max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }

    print(f"Research Agent chat. artifact_version={artifact_version.artifact_version}")
    if args.use_voice:
        print("Chế độ giọng nói: nói vào mic để nhập, kết quả sẽ được đọc bằng giọng nói.")
    print("Type /exit to stop.")

    history: list[dict[str, str]] = []
    turn_index = 0
    while True:
        try:
            if args.use_voice:
                from stt import speak_input
                print("\n🎤 Đang nghe... (nói câu hỏi của bạn)")
                try:
                    user_text = (speak_input() or "").strip()
                except Exception as exc:
                    print(f"⚠️  Không nhận được giọng nói: {exc}")
                    continue
            else:
                user_text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_text:
            continue
        if user_text in {"/exit", "/quit"}:
            break

        turn_index += 1
        messages = [
            {"role": "system", "content": system_prompt},
            *trim_history(history, args.history_window),
            {"role": "user", "content": user_text},
        ]

        turn_record: dict[str, Any] = {
            "turn_index": turn_index,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }

        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=args.model,
                max_tool_rounds=args.max_tool_rounds,
            )
            turn_record.update(result)
            assistant_text = result["assistant_text"]
            print(f"\nAgent> {assistant_text}")
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": assistant_text})

            if assistant_text:
                try:
                    from stt import speak_output
                    speak_output(assistant_text, voice_type=args.voice_type)
                except Exception as exc:
                    print(f"⚠️  Không thể đọc kết quả bằng giọng nói: {exc}")
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {str(exc)}",
            })
            print(f"\nERROR> {turn_record['error']}")

        turn_record["ended_at"] = now_iso()
        transcript["turns"].append(turn_record)
        write_transcript(transcript_path, transcript)
        print(f"Transcript saved: {transcript_path}")

    write_transcript(transcript_path, transcript)
    print(f"Final transcript: {transcript_path}")


if __name__ == "__main__":
    main()
