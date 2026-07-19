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
            # Lowered from 4000 after adding the tra_gia/tra_cuu/xem_lich_kham tool
            # descriptions grew the system prompt. Lowered again from 3000 -- with
            # the HỒ SƠ BỆNH NHÂN (patient profile) block injected too, prompt_tokens
            # reached ~5368, still tripping the 413 at 3000. Lowered again from 2500
            # after adding the THU THẬP TRIỆU CHỨNG guidance (deeper symptom
            # gathering before concluding) grew the prompt further -- confirmed live.
            max_tokens=1800,
        )

    def _extra_body(self, model: str) -> dict[str, Any] | None:
        if model.startswith("qwen/qwen3"):
            # For complex prompts (hospital pricing rules + triage + doctor-routing
            # all combined) this model would burn its ENTIRE completion budget on
            # hidden reasoning and never write the actual JSON (finish_reason
            # "length", reasoning_tokens == max_tokens, content=""). The system
            # prompt already spells out the exact reasoning steps, so the model's
            # own open-ended "thinking" isn't needed -- reasoning_effort="none"
            # disables thinking-token generation outright (stronger than
            # reasoning_format="hidden", which still generates them, just hides
            # them from the response).
            return {"reasoning_effort": "none"}
        return None
