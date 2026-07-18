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


class OpenAIProvider:
    """OpenAI Chat Completions provider with normalized tool_calls output."""

    def __init__(
        self,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str | None = None,
        default_model: str = "gpt-4o-mini",
        max_tokens: int | None = None,
    ) -> None:
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.default_model = default_model
        self.max_tokens = max_tokens

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
            "messages": messages,
            "temperature": temperature,
        }
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
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
            calls.append(ToolCall(name=call.function.name, args=args))
        return ModelResponse(text=msg.content, tool_calls=calls, raw=resp)
