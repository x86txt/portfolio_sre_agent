from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from app.api.state import engine, events
from app.triage.models import CamelModel, Provider
from app.triage.normalize.normalize import normalize_payload

router = APIRouter()


class IngestRequest(CamelModel):
    provider: Optional[str] = None
    payload: Dict[str, Any]


class IngestResponse(CamelModel):
    incident_ids: List[str]
    events_ingested: int


def _parse_provider(value: str | None) -> Provider | None:
    if not value:
        return None
    v = value.strip().lower()
    for p in Provider:
        if p.value == v:
            return p
    return None


@router.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    provider = _parse_provider(req.provider)
    alert_events = normalize_payload(provider=provider, payload=req.payload)

    incident_ids: list[str] = []
    for ev in alert_events:
        inc = engine.ingest_event(ev)
        incident_ids.append(inc.id)
        events.publish(event="alert_ingested", data={"incidentId": inc.id, "service": inc.service, "env": inc.env})
        events.publish(event="incident_updated", data=inc.model_dump(by_alias=True))

    # de-dupe ids while preserving order
    seen = set()
    incident_ids_unique: list[str] = []
    for iid in incident_ids:
        if iid in seen:
            continue
        seen.add(iid)
        incident_ids_unique.append(iid)

    return IngestResponse(incident_ids=incident_ids_unique, events_ingested=len(alert_events))


