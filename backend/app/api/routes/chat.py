from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.triage.llm.factory import get_llm_client
from app.triage.models import CamelModel, LlmMode
from app.triage.rate_limit import rate_limiter

router = APIRouter()

# Maximum prompt length (characters) - reasonable limit for LLM context
MAX_PROMPT_LENGTH = 10000


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent injection attacks.

    - Strips HTML/XML tags (prevents script injection)
    - Removes control characters (except newlines and tabs)
    - Truncates to MAX_PROMPT_LENGTH
    - Strips leading/trailing whitespace

    Note: We don't escape HTML entities here since the text goes to an LLM API,
    not directly to HTML output. The LLM should receive clean, readable text.
    """
    if not text:
        return ""
    
    # Remove HTML/XML tags (prevents script injection and keeps text clean)
    text = re.sub(r"<[^>]+>", "", text)
    
    # Remove control characters except newline (\n) and tab (\t)
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    
    # Truncate to max length
    if len(text) > MAX_PROMPT_LENGTH:
        text = text[:MAX_PROMPT_LENGTH] + "... [truncated]"
    
    # Strip whitespace
    text = text.strip()
    
    return text


class ChatRequest(CamelModel):
    prompt: str
    llm: LlmMode = LlmMode.auto
    model: str | None = None


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


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    """
    Lightweight SRE chat endpoint.

    Takes a free-form prompt with telemetry/incident context and returns a
    concise answer from the configured LLM (or 503 if none is configured).
    
    Rate limited to 3 LLM API calls per hour per IP address.
    """
    # Validate and sanitize input
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    sanitized_prompt = sanitize_input(req.prompt)
    
    if not sanitized_prompt:
        raise HTTPException(status_code=400, detail="Prompt is empty after sanitization")
    
    client = get_llm_client(req.llm)
    if not client:
        raise HTTPException(
            status_code=503,
            detail="No LLM provider is configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.",
        )
    
    # Check rate limit before calling LLM
    client_ip = _get_client_ip(request)
    allowed, remaining = rate_limiter.check_rate_limit(client_ip)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum 3 LLM API calls per hour. Please try again later.",
            headers={
                "X-RateLimit-Limit": "3",
                "X-RateLimit-Remaining": "0",
                "Retry-After": "3600",
            },
        )

    system = (
        "You are an experienced SRE and incident commander.\n"
        "Given the user's metrics, logs or deployment notes, decide whether there "
        "is cause for concern and what concrete steps to take.\n"
        "Be concise but specific. When saturation is high but latency/errors are "
        "normal, treat it as a capacity warning rather than an outage.\n"
    )

    if req.model and hasattr(client, "model"):
        setattr(client, "model", req.model)

    try:
        out = await client.generate(system=system, prompt=sanitized_prompt, temperature=0.2)
        # Include rate limit headers in response
        response = PlainTextResponse(out.text.strip() + "\n", media_type="text/plain")
        response.headers["X-RateLimit-Limit"] = "3"
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1 if remaining is not None else "?")
        return response
    except RuntimeError as e:
        # LLM client raised a runtime error (API errors, etc.)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


