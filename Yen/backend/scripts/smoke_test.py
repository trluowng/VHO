"""
Smoke test for the Bệnh viện Tim Hà Nội assistant.

Runs the in-process triage() flow (text-in -> text-out) against data/smoke_cases.json
and reports three metrics:

  - accuracy : fraction of expected keywords present in the assistant's text output
  - latency  : per-call wall-clock time (ms), mean / p95
  - recall   : fraction of `expect_span` anchors recovered across all cases

Usage:
    py scripts/smoke_test.py --provider groq --model qwen/qwen3-32b
    py scripts/smoke_test.py --provider gemini
    py scripts/smoke_test.py --max-cases 4          # subset

The model call needs a live provider API key (GROQ_API_KEY / GEMINI_API_KEY ...).
If the provider errors, the case is reported as a provider_error and excluded from
accuracy/recall but kept in latency as a failed call.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def extract_text(payload: dict) -> str:
    """Pull all human-readable text out of the triage JSON response (events + profile)."""
    parts: list[str] = []
    for ev in payload.get("events", []) or []:
        t = ev.get("type")
        if t == "message":
            parts.append(ev.get("text", ""))
        elif t == "question":
            parts.append(ev.get("text", ""))
        elif t == "result":
            tri = ev.get("triage", {}) or {}
            parts.append(tri.get("reason", ""))
            for a in tri.get("actions", []) or []:
                parts.append(str(a))
    prof = payload.get("profile", {}) or {}
    for s in prof.get("symptoms", []) or []:
        parts.append(s.get("label", ""))
    return "\n".join(p for p in parts if p)


def run_case(triage_fn, case: dict) -> dict:
    start = time.perf_counter()
    try:
        payload = triage_fn({"message": case["input"]}, None)
        text = extract_text(payload)
        error = None
    except Exception as exc:
        text = ""
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = (time.perf_counter() - start) * 1000

    expected = [k.lower() for k in case.get("expect_keywords", [])]
    hay = text.lower()
    hits = [k for k in expected if k in hay]
    accuracy = (len(hits) / len(expected)) if expected else (1.0 if text else 0.0)

    span = case.get("expect_span")
    recall_hit = bool(span) and (span.lower() in hay)

    return {
        "id": case["id"],
        "latency_ms": round(elapsed_ms, 1),
        "accuracy": round(accuracy, 4),
        "keywords_hit": hits,
        "keywords_total": len(expected),
        "recall_hit": recall_hit,
        "provider_error": error,
        "output_preview": text[:240].replace("\n", " "),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test: accuracy / latency / recall.")
    parser.add_argument("--provider", required=True, help="Provider name, e.g. groq, gemini, openai")
    parser.add_argument("--model", default=None)
    parser.add_argument("--cases", type=Path, default=DATA_DIR / "smoke_cases.json")
    parser.add_argument("--max-cases", type=int, default=0, help="Limit number of cases (0 = all)")
    args = parser.parse_args()

    # Import the server's in-process triage flow (sets up provider + memory).
    # Text-only smoke test: stub out the `stt` module so speak_output is a no-op and
    # never imports config / speech_recognition / pygame.
    import types

    sys.path.insert(0, str(ROOT))
    _stt_stub = types.ModuleType("stt")
    _stt_stub.speak_input = lambda *a, **k: ""
    _stt_stub.speak_output = lambda *a, **k: None
    sys.modules["stt"] = _stt_stub
    import server as srv

    provider_name = args.provider
    srv.PROVIDER_NAME = provider_name
    srv.PROVIDER = srv.make_provider(provider_name)
    srv.SELECTED_MODEL = args.model or getattr(srv.PROVIDER, "default_model", None)

    data = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = data["cases"]
    if args.max_cases:
        cases = cases[: args.max_cases]

    results = [run_case(srv.triage, c) for c in cases]

    latencies = [r["latency_ms"] for r in results]
    measured = [r for r in results if not r["provider_error"]]
    acc_vals = [r["accuracy"] for r in measured] or [0.0]
    recalls = [1 if r["recall_hit"] else 0 for r in measured]

    summary = {
        "provider": provider_name,
        "model": srv.SELECTED_MODEL,
        "total_cases": len(results),
        "provider_error_cases": len(results) - len(measured),
        "accuracy_mean": round(statistics.mean(acc_vals), 4),
        "recall_mean": round(statistics.mean(recalls), 4) if recalls else 0.0,
        "latency_ms_mean": round(statistics.mean(latencies), 1) if latencies else 0.0,
        "latency_ms_p95": round(sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0.0, 1),
        "latency_ms_max": round(max(latencies), 1) if latencies else 0.0,
    }

    print("\n=== SMOKE TEST RESULTS ===")
    for r in results:
        flag = "ERR " if r["provider_error"] else "ok  "
        print(f"[{flag}] {r['id']:<26} acc={r['accuracy']:.2f} "
              f"recall={'Y' if r['recall_hit'] else 'N'} lat={r['latency_ms']:>7.1f}ms "
              f"| {r['output_preview']}")
    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    out = {"summary": summary, "results": results}
    out_path = ROOT / "runs" / "smoke_test.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
