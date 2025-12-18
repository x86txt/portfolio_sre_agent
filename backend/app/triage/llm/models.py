from __future__ import annotations

import os
from typing import Dict, List, Optional

import httpx


_OVERRIDE_WEIGHTS: Optional[Dict[str, float]] = None


def set_override_weights(weights: Optional[Dict[str, float]]) -> None:
    """
    Override LLM weights at runtime (used by the API/UI).

    When None, we fall back to AITRIAGE_LLM_WEIGHTS from the environment.
    """
    global _OVERRIDE_WEIGHTS
    _OVERRIDE_WEIGHTS = dict(weights) if weights is not None else None


def parse_weights() -> Dict[str, float]:
    """
    Resolve weights from overrides (if set) or from AITRIAGE_LLM_WEIGHTS.

    Example env format: "openai:3,anthropic:1".
    """
    if _OVERRIDE_WEIGHTS is not None:
        return dict(_OVERRIDE_WEIGHTS)

    raw = os.getenv("AITRIAGE_LLM_WEIGHTS", "")
    weights: Dict[str, float] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            continue
        name, w = part.split(":", 1)
        name = name.strip().lower()
        try:
            weights[name] = float(w)
        except ValueError:
            continue
    return weights


PREFERRED_OPENAI_MODELS: List[str] = [
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4",
]

PREFERRED_ANTHROPIC_MODELS: List[str] = [
    # Claude 4.5 family (latest)
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001",
    # Claude 3.5 family (previous generation)
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    # Claude 3 Opus
    "claude-3-opus-20240229",
    # "latest" aliases (if you prefer auto-updates)
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-latest",
    "claude-3-opus-latest",
]


async def list_openai_models(api_key: str) -> List[str]:
    if not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        # Fall back to a curated list if listing fails.
        return PREFERRED_OPENAI_MODELS

    models: List[str] = []
    for item in data.get("data", []) or []:
        if not isinstance(item, dict):
            continue
        mid = item.get("id")
        if isinstance(mid, str):
            models.append(mid)
    if not models:
        return PREFERRED_OPENAI_MODELS
    # Deduplicate while preserving order.
    seen = set()
    out: List[str] = []
    for m in models:
        if m in seen:
            continue
        seen.add(m)
        out.append(m)
    return out


async def list_anthropic_models() -> List[str]:
    # Anthropic does not currently expose a public "list models" endpoint.
    # For this portfolio project we return a curated static list.
    return PREFERRED_ANTHROPIC_MODELS


