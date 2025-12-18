from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from app.triage.llm.base import LlmClient, LlmOutput


class AnthropicClient(LlmClient):
    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        # Default to Claude 4.5 Sonnet (latest) if not overridden.
        self.model = os.getenv("AITRIAGE_ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    def available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, *, system: str, prompt: str, temperature: float = 0.2) -> LlmOutput:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 900,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                error_text = resp.text
                raise RuntimeError(
                    f"Anthropic API error {resp.status_code}: {error_text}\n"
                    f"Model: {self.model}, Request body keys: {list(body.keys())}"
                )
            data = resp.json()

        content = data.get("content") or []
        # Newer anthropic message API returns list of blocks; take first text block.
        text = ""
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                text = first.get("text") or ""
        return LlmOutput(text=text, provider="anthropic", model=self.model)


