from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmOutput:
    text: str
    provider: str
    model: str


class LlmClient:
    async def generate(self, *, system: str, prompt: str, temperature: float = 0.2) -> LlmOutput:  # pragma: no cover
        raise NotImplementedError


