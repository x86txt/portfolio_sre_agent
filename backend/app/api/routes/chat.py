from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.triage.llm.factory import get_llm_client
from app.triage.models import CamelModel, LlmMode

router = APIRouter()


class ChatRequest(CamelModel):
    prompt: str
    llm: LlmMode = LlmMode.auto
    model: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Lightweight SRE chat endpoint.

    Takes a free-form prompt with telemetry/incident context and returns a
    concise answer from the configured LLM (or 503 if none is configured).
    """
    client = get_llm_client(req.llm)
    if not client:
        raise HTTPException(
            status_code=503,
            detail="No LLM provider is configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.",
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
        out = await client.generate(system=system, prompt=req.prompt, temperature=0.2)
        return PlainTextResponse(out.text.strip() + "\n", media_type="text/plain")
    except RuntimeError as e:
        # LLM client raised a runtime error (API errors, etc.)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


