from __future__ import annotations

import json
import os
import re
from typing import Any

from providers.base import ModelResponse, ToolCall

# Groq occasionally emits tool calls in a malformed text pseudo-XML instead of
# proper structured function-calling (known issue with reasoning models on Groq,
# more common with reasoning disabled) -- when that happens the API answers with
# a 400 "tool_use_failed" instead of the normal response, but still includes the
# model's attempt in "failed_generation". Recover the call from that text rather
# than losing the turn outright.
_TOOL_CALL_FN_RE = re.compile(r"<function=([a-zA-Z_][a-zA-Z0-9_]*)")
_TOOL_CALL_PARAM_RE = re.compile(r"<parameter=([a-zA-Z_][a-zA-Z0-9_]*)>\s*(.*?)\s*</parameter>", re.DOTALL)


def _extract_failed_generation(exc: Exception) -> str | None:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, dict) and error.get("code") == "tool_use_failed":
            return error.get("failed_generation")
    return None


def _recover_tool_call(failed_generation: str) -> ToolCall | None:
    fn_match = _TOOL_CALL_FN_RE.search(failed_generation)
    if not fn_match:
        return None
    args: dict[str, Any] = {}
    for param_match in _TOOL_CALL_PARAM_RE.finditer(failed_generation):
        args[param_match.group(1)] = param_match.group(2).strip()
    return ToolCall(name=fn_match.group(1), args=args)


def _to_wire_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate chat.py's provider-neutral message list into the real OpenAI
    Chat Completions wire format for tool calls.

    chat.py builds a single history shared across all providers (including
    Gemini, which has its own distinct message shape and just reads `content`
    as plain text). For a tool-calling turn it therefore embeds the call/result
    JSON as readable text in `content`, AND -- only for providers that need it
    -- attaches the real structured data under `tool_calls` / `tool_results`
    keys. Confirmed via live testing that real OpenAI models (gpt-4o-mini)
    silently ignore/mistrust the text-only form (the assistant message lacks
    a real `tool_calls` array and there's no matching `role: "tool"` reply),
    so this rebuilds the exact protocol OpenAI expects instead of trusting
    the text embedding.
    """
    wire: list[dict[str, Any]] = []
    for msg in messages:
        tool_calls = msg.get("tool_calls")
        tool_results = msg.get("tool_results")
        if tool_calls:
            wire.append({
                "role": "assistant",
                "content": msg.get("text") or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"], ensure_ascii=False),
                        },
                    }
                    for tc in tool_calls
                ],
            })
        elif tool_results:
            for tr in tool_results:
                wire.append({"role": "tool", "tool_call_id": tr["tool_call_id"], "content": tr["content"]})
        else:
            wire.append({"role": msg["role"], "content": msg.get("content", "")})
    return wire


# Real OpenAI's json_schema "strict" mode enforces this shape at the token-sampling level --
# unlike prompt instructions (which gpt-4o-mini kept ignoring live: it repeatedly collapsed a
# "result" + "question" pair into a single "message" event no matter how explicit the prompt's
# rule + worked example were), the model literally cannot emit a differently-shaped object.
# Strict mode requires every property to appear in "required" (no true-optional keys) and
# "additionalProperties": false everywhere -- fields that only apply to some event types are
# expressed as nullable (`["string", "null"]`) instead of omitted.
_TRIAGE_TRIAGE_SCHEMA: dict[str, Any] = {
    "type": ["object", "null"],
    "properties": {
        "level": {"type": "string", "enum": ["green", "amber", "red"]},
        "eyebrow": {"type": "string"},
        "label": {"type": "string"},
        "icon": {"type": "string"},
        "reason": {"type": "string"},
        "conditions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "pct": {"type": ["string", "null"]}},
                "required": ["name", "pct"],
                "additionalProperties": False,
            },
        },
        "actions": {"type": "array", "items": {"type": "string"}},
        "missing": {"type": "array", "items": {"type": "string"}},
        "confTier": {"type": "string", "enum": ["low", "mid", "high"]},
        "confidence": {"type": "integer"},
        "ctas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"label": {"type": "string"}, "kind": {"type": "string", "enum": ["primary", "ghost"]}},
                "required": ["label", "kind"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["level", "eyebrow", "label", "icon", "reason", "conditions", "actions", "missing", "confTier", "confidence", "ctas"],
    "additionalProperties": False,
}

_TRIAGE_EVENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["message", "question", "result", "emergency"]},
        "text": {"type": ["string", "null"]},
        "confirm": {"type": ["boolean", "null"]},
        "quick": {"type": ["array", "null"], "items": {"type": "string"}},
        "triage": _TRIAGE_TRIAGE_SCHEMA,
        "flag": {"type": ["string", "null"]},
    },
    "required": ["type", "text", "confirm", "quick", "triage", "flag"],
    "additionalProperties": False,
}

_TRIAGE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "events": {"type": "array", "items": _TRIAGE_EVENT_SCHEMA},
        "profile": {
            "type": "object",
            "properties": {
                "stage": {"type": "string", "enum": ["intake", "questioning", "done", "emergency"]},
                "symptoms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"label": {"type": "string"}, "specific": {"type": "boolean"}},
                        "required": ["label", "specific"],
                        "additionalProperties": False,
                    },
                },
                "confidence": {"type": "integer"},
                "confTier": {"type": "string", "enum": ["none", "low", "mid", "high"]},
                "missing": {"type": "array", "items": {"type": "string"}},
                "facts": {
                    "type": "object",
                    "properties": {
                        "duration": {"type": ["string", "null"]},
                        "severity": {"type": ["string", "null"]},
                        "associated": {"type": ["boolean", "null"]},
                    },
                    "required": ["duration", "severity", "associated"],
                    "additionalProperties": False,
                },
            },
            "required": ["stage", "symptoms", "confidence", "confTier", "missing", "facts"],
            "additionalProperties": False,
        },
    },
    "required": ["events", "profile"],
    "additionalProperties": False,
}


class OpenAIProvider:
    """OpenAI Chat Completions provider with normalized tool_calls output."""

    def __init__(
        self,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str | None = None,
        default_model: str = "gpt-4o-mini",
        max_tokens: int | None = None,
        use_structured_output: bool = False,
    ) -> None:
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.default_model = default_model
        self.max_tokens = max_tokens
        # Off by default: Groq/OpenRouter's OpenAI-compatible endpoints don't reliably support
        # strict json_schema mode the same way real OpenAI does -- only the "openai" provider
        # registry entry opts in (see providers/__init__.py).
        self.use_structured_output = use_structured_output

    def _extra_body(self, model: str) -> dict[str, Any] | None:
        """Return provider-specific Chat Completions parameters."""
        return None

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: Any | None = None,
    ) -> ModelResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install live provider dependency first: pip install openai") from exc

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key env var: {self.api_key_env}")

        client = OpenAI(api_key=api_key, base_url=self.base_url)
        selected_model = model or self.default_model
        kwargs: dict[str, Any] = {
            "model": selected_model,
            "messages": _to_wire_messages(messages),
            "temperature": temperature,
        }
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if self.use_structured_output:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "yen_triage_response", "strict": True, "schema": _TRIAGE_RESPONSE_SCHEMA},
            }
        extra_body = self._extra_body(selected_model)
        if extra_body:
            kwargs["extra_body"] = extra_body

        try:
            resp = client.chat.completions.create(**kwargs)
        except Exception as exc:
            failed_generation = _extract_failed_generation(exc)
            if failed_generation:
                recovered = _recover_tool_call(failed_generation)
                if recovered:
                    return ModelResponse(text=None, tool_calls=[recovered], raw=None)
            raise

        msg = resp.choices[0].message
        calls: list[ToolCall] = []
        for call in msg.tool_calls or []:
            args = json.loads(call.function.arguments or "{}")
            calls.append(ToolCall(name=call.function.name, args=args, id=call.id))
        # qwen3 (and other reasoning models) may wrap output in a <think>...</think>
        # block; strip it so the visible text isn't empty.
        text = msg.content or ""
        if "<think>" in text:
            text = text.split("</think>", 1)[-1].strip()
        return ModelResponse(text=text or None, tool_calls=calls, raw=resp)
