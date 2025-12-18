from __future__ import annotations

import os
from typing import Dict, List

from fastapi import APIRouter

from app.triage.llm.models import (
    PREFERRED_ANTHROPIC_MODELS,
    PREFERRED_OPENAI_MODELS,
    list_anthropic_models,
    list_openai_models,
    parse_weights,
    set_override_weights,
)
from app.triage.models import CamelModel

router = APIRouter()


class LlmProviderInfo(CamelModel):
    id: str
    weight: float
    available: bool
    default_model: str | None = None
    models: List[str] = []


class LlmModelsResponse(CamelModel):
    providers: List[LlmProviderInfo]
    auto_order: List[str]


class LlmWeightsUpdate(CamelModel):
    weights: Dict[str, float]


@router.get("/llm/models", response_model=LlmModelsResponse)
async def get_llm_models() -> LlmModelsResponse:
    weights = parse_weights()

    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    openai_models: List[str] = []
    anthropic_models: List[str] = []

    if openai_key:
        openai_models = await list_openai_models(openai_key)
    if anthropic_key:
        anthropic_models = await list_anthropic_models()

    providers: List[LlmProviderInfo] = []

    if openai_key:
        env_default = os.getenv("AITRIAGE_OPENAI_MODEL", "")
        default_model = (
            env_default
            or next((m for pref in PREFERRED_OPENAI_MODELS for m in openai_models if m.startswith(pref)), None)
            or (openai_models[0] if openai_models else None)
        )
        providers.append(
            LlmProviderInfo(
                id="openai",
                weight=weights.get("openai", 1.0),
                available=True,
                default_model=default_model,
                models=openai_models or PREFERRED_OPENAI_MODELS,
            )
        )
    else:
        providers.append(
            LlmProviderInfo(
                id="openai",
                weight=weights.get("openai", 1.0),
                available=False,
                default_model=None,
                models=[],
            )
        )

    if anthropic_key:
        env_default = os.getenv("AITRIAGE_ANTHROPIC_MODEL", "")
        default_model = (
            env_default
            or next(
                (m for pref in PREFERRED_ANTHROPIC_MODELS for m in anthropic_models if m.startswith(pref)),
                None,
            )
            or (anthropic_models[0] if anthropic_models else None)
        )
        providers.append(
            LlmProviderInfo(
                id="anthropic",
                weight=weights.get("anthropic", 1.0),
                available=True,
                default_model=default_model,
                models=anthropic_models or PREFERRED_ANTHROPIC_MODELS,
            )
        )
    else:
        providers.append(
            LlmProviderInfo(
                id="anthropic",
                weight=weights.get("anthropic", 1.0),
                available=False,
                default_model=None,
                models=[],
            )
        )

    # auto_order: highest weight first, then name; only include available providers.
    auto_candidates = [p for p in providers if p.available]
    auto_order = [p.id for p in sorted(auto_candidates, key=lambda p: (-p.weight, p.id))]

    return LlmModelsResponse(providers=providers, auto_order=auto_order)


@router.post("/llm/weights", response_model=LlmModelsResponse)
async def update_llm_weights(body: LlmWeightsUpdate) -> LlmModelsResponse:
    """
    Update LLM weights at runtime (e.g. openai:3, anthropic:1).

    This overrides AITRIAGE_LLM_WEIGHTS for the running process.
    """
    # Normalise provider ids to lowercase.
    clean: Dict[str, float] = {}
    for k, v in body.weights.items():
        k2 = k.strip().lower()
        try:
            clean[k2] = float(v)
        except (TypeError, ValueError):
            continue

    set_override_weights(clean or None)
    # Return the effective model list with the new weights applied.
    return await get_llm_models()


