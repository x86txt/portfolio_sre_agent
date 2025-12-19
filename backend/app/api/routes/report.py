from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.state import store
from app.triage.cache import cache
from app.triage.llm.factory import get_llm_client
from app.triage.models import LlmMode, ReportFormat
from app.triage.rate_limit import rate_limiter
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


def _get_client_ip(request: Request) -> str:
    """Extract client IP address from request, handling proxies."""
    # Check for X-Forwarded-For header (from Fly.io/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


@router.post("/incidents/{incident_id}/report")
async def report_incident(
    incident_id: str,
    request: Request,
    format: ReportFormat = Query(default=ReportFormat.markdown),
    llm: LlmMode = Query(default=LlmMode.auto),
    model: str | None = Query(default=None, description="Optional model override for the chosen LLM provider."),
) -> Any:
    """
    Generate a situation report for an incident.
    
    Rate limited to 3 LLM API calls per hour per IP address (shared across all endpoints).
    Cached reports and deterministic fallback do not count toward the limit.
    """
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
        
        # Check cache first (cached results don't count toward rate limit)
        cache_key_model = f"{llm.value}:{effective_model}"
        cached_content = cache.get(incident_id, cache_key_model, format.value)
        
        if cached_content:
            # Return cached content (no rate limit check needed)
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

        # Check rate limit before calling LLM (only when actually making an LLM call)
        client_ip = _get_client_ip(request)
        allowed, remaining = rate_limiter.check_rate_limit(client_ip)
        
        if not allowed:
            # Rate limited - fall back to deterministic output
            if format == ReportFormat.json:
                return report_obj
            if format == ReportFormat.text:
                return PlainTextResponse(render_text(report_obj), media_type="text/plain")
            return PlainTextResponse(render_markdown(report_obj), media_type="text/markdown")

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
                
                # Return JSON with rate limit headers
                response = JSONResponse(content=report_obj)
                response.headers["X-RateLimit-Limit"] = "3"
                response.headers["X-RateLimit-Remaining"] = str(remaining - 1 if remaining is not None else "?")
                return response

            # Cache the markdown/text response
            cache.set(incident_id, cache_key_model, format.value, generated_text)
            
            media = "text/markdown" if format == ReportFormat.markdown else "text/plain"
            response = PlainTextResponse(generated_text + "\n", media_type=media)
            response.headers["X-RateLimit-Limit"] = "3"
            response.headers["X-RateLimit-Remaining"] = str(remaining - 1 if remaining is not None else "?")
            return response
        except Exception:
            # Fall back to deterministic output.
            pass

    # Deterministic fallback (no LLM, no cache needed)
    if format == ReportFormat.json:
        return report_obj
    if format == ReportFormat.text:
        return PlainTextResponse(render_text(report_obj), media_type="text/plain")
    return PlainTextResponse(render_markdown(report_obj), media_type="text/markdown")


