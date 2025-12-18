from __future__ import annotations

import os
from typing import Dict, List, Tuple

from app.triage.llm.anthropic_client import AnthropicClient
from app.triage.llm.base import LlmClient
from app.triage.llm.models import parse_weights
from app.triage.llm.openai_client import OpenAiClient
from app.triage.models import LlmMode


def _pick_by_weight(clients: Dict[str, LlmClient]) -> LlmClient | None:
    """
    Choose a client based on AITRIAGE_LLM_WEIGHTS, falling back to a stable order.
    """
    if not clients:
        return None

    weights = parse_weights()
    scored: List[Tuple[float, str, LlmClient]] = []
    for name, client in clients.items():
        w = weights.get(name, 1.0)
        scored.append((w, name, client))

    # Highest weight first, then name for stability.
    scored.sort(key=lambda t: (-t[0], t[1]))
    return scored[0][2] if scored else None


def get_llm_client(mode: LlmMode) -> LlmClient | None:
    """
    Returns a configured LLM client or None if unavailable.

    - mode=openai|anthropic: pick that provider if configured.
    - mode=auto:
        * if AITRIAGE_LLM_PROVIDER is set, prefer that
        * else use weights from AITRIAGE_LLM_WEIGHTS (e.g. \"openai:2,anthropic:1\")
        * else fall back to OpenAI, then Anthropic.
    """

    if mode == LlmMode.off:
        return None

    if mode == LlmMode.openai:
        c = OpenAiClient()
        return c if c.available() else None

    if mode == LlmMode.anthropic:
        c = AnthropicClient()
        return c if c.available() else None

    # auto
    provider = (os.getenv("AITRIAGE_LLM_PROVIDER") or "").strip().lower()
    if provider == "anthropic":
        c = AnthropicClient()
        return c if c.available() else None
    if provider == "openai":
        c = OpenAiClient()
        return c if c.available() else None

    # No explicit provider: choose based on weights and availability.
    candidates: Dict[str, LlmClient] = {}
    o = OpenAiClient()
    if o.available():
        candidates["openai"] = o
    a = AnthropicClient()
    if a.available():
        candidates["anthropic"] = a

    chosen = _pick_by_weight(candidates)
    if chosen:
        return chosen

    return None


