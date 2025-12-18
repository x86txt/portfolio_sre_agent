from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from app.triage.llm.base import LlmClient, LlmOutput


class OpenAiClient(LlmClient):
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("AITRIAGE_OPENAI_MODEL", "gpt-4o-mini")

    def available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, *, system: str, prompt: str, temperature: float = 0.2) -> LlmOutput:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body: Dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        text = (
            (((data.get("choices") or [])[0] or {}).get("message") or {}).get("content")
            or ""
        )
        return LlmOutput(text=text, provider="openai", model=self.model)


