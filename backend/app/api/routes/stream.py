from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.state import events

router = APIRouter()


@router.get("/stream")
async def stream():
    return StreamingResponse(events.subscribe(), media_type="text/event-stream")


