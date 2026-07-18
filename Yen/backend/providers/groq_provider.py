from __future__ import annotations

import os
from typing import Any

from providers.openai_provider import OpenAIProvider


class GroqProvider(OpenAIProvider):
    """Groq Chat Completions via its OpenAI-compatible API."""

    def __init__(self) -> None:
        super().__init__(
            api_key_env="GROQ_API_KEY",
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            # qwen/qwen3-32b was deprecated by Groq on 2026-06-17; qwen3.6-27b is the
            # current Qwen model on their platform (see console.groq.com/docs/models).
            default_model="qwen/qwen3.6-27b",
            # Reasoning models can burn their whole completion budget on the hidden
            # "reasoning" channel and get cut off (finish_reason "length") before
            # writing any actual JSON -- the old default (~2048) wasn't enough. But
            # this free/on-demand tier also caps *requested* tokens-per-minute at
            # 8000 (prompt + max_tokens counted together), so this can't just be set
            # to the max -- tuned to leave headroom for the system prompt + history.
            max_tokens=4000,
        )

    def _extra_body(self, model: str) -> dict[str, Any] | None:
        if model.startswith("qwen/qwen3"):
            # Keep private reasoning out of the visible response so the triage
            # endpoint receives only the JSON requested by its system prompt.
            return {"reasoning_format": "hidden"}
        return None
