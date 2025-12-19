from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.api.state import store
from app.triage.cache import cache
from app.triage.llm.factory import get_llm_client
from app.triage.models import LlmMode, ReportFormat
from app.triage.report.generate import generate_report_object
from app.triage.report.render import render_markdown, render_text
from app.triage.utils import stable_json_dumps

router = APIRouter()


def _report_system_prompt() -> str:
    return (
        "You are an expert SRE writing a concise situation report.\n"
        "Be precise, avoid fluff, and do not invent metrics.\n"
        "If saturation is high but latency/errors are normal, treat it as a capacity warning.\n"
    )


def _report_user_prompt(*, report: Dict[str, Any], fmt: ReportFormat) -> str:
    return (
        f"Generate a situation report in {fmt.value}.\n\n"
        "Include:\n"
        "- Summary (1-3 sentences)\n"
        "- Signals (saturation, latency, errors) with state/trend and observed vs threshold\n"
        "- Suggested runbook steps (verify/mitigate/confirm)\n\n"
        "Incident JSON:\n"
        f"{stable_json_dumps(report)}\n"
    )


@router.post("/incidents/{incident_id}/report")
async def report_incident(
    incident_id: str,
    format: ReportFormat = Query(default=ReportFormat.markdown),
    llm: LlmMode = Query(default=LlmMode.auto),
    model: str | None = Query(default=None, description="Optional model override for the chosen LLM provider."),
) -> Any:
    incident = store.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    report_obj = generate_report_object(incident)

    client = get_llm_client(llm)
    if client:
        # Determine the effective model name for cache key
        effective_model = model
        if not effective_model and hasattr(client, "model"):
            effective_model = getattr(client, "model", "default")
        if not effective_model:
            effective_model = "default"
        
        # Check cache first
        cache_key_model = f"{llm.value}:{effective_model}"
        cached_content = cache.get(incident_id, cache_key_model, format.value)
        
        if cached_content:
            # Return cached content
            if format == ReportFormat.json:
                # For JSON, parse the cached content
                try:
                    cached_obj = json.loads(cached_content)
                    return cached_obj
                except json.JSONDecodeError:
                    # If parsing fails, fall through to regenerate
                    pass
            else:
                # For markdown/text, return as-is
                media = "text/markdown" if format == ReportFormat.markdown else "text/plain"
                return PlainTextResponse(cached_content, media_type=media)

        try:
            # Optional per-request model override when the client supports it.
            if model and hasattr(client, "model"):
                setattr(client, "model", model)

            out = await client.generate(
                system=_report_system_prompt(),
                prompt=_report_user_prompt(report=report_obj, fmt=format),
                temperature=0.2,
            )
            
            generated_text = out.text.strip()
            
            # For json, keep the deterministic shape and attach the narrative.
            if format == ReportFormat.json:
                report_obj["llmNarrative"] = generated_text
                report_obj["llmProvider"] = out.provider
                report_obj["llmModel"] = out.model
                
                # Cache the JSON response
                cache.set(incident_id, cache_key_model, format.value, json.dumps(report_obj, default=str))
                
                return report_obj

            # Cache the markdown/text response
            cache.set(incident_id, cache_key_model, format.value, generated_text)
            
            media = "text/markdown" if format == ReportFormat.markdown else "text/plain"
            return PlainTextResponse(generated_text + "\n", media_type=media)
        except Exception:
            # Fall back to deterministic output.
            pass

    # Deterministic fallback (no LLM, no cache needed)
    if format == ReportFormat.json:
        return report_obj
    if format == ReportFormat.text:
        return PlainTextResponse(render_text(report_obj), media_type="text/plain")
    return PlainTextResponse(render_markdown(report_obj), media_type="text/markdown")


