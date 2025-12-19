from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.api.state import events, store
from app.triage.cache import cache
from app.triage.models import CamelModel, Incident, IncidentStatus, ResolutionStatus

router = APIRouter()


class ResolutionUpdateRequest(CamelModel):
  status: ResolutionStatus
  note: Optional[str] = None


@router.post("/incidents/{incident_id}/resolution", response_model=Incident)
def update_resolution(incident_id: str, body: ResolutionUpdateRequest) -> Incident:
    incident = store.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.resolution_status = body.status
    incident.resolution_note = body.note

    # If the user explicitly resolves/auto-closes/accepts the incident,
    # treat it as resolved in the lifecycle as well.
    if body.status in {
        ResolutionStatus.resolved,
        ResolutionStatus.auto_closed,
        ResolutionStatus.false_alert,
        ResolutionStatus.accepted,
    }:
        incident.status = IncidentStatus.resolved

    store.upsert(incident)
    
    # Invalidate cached reports for this incident (resolution status changed)
    cache.invalidate_incident(incident_id)
    
    events.publish(event="incident_updated", data=incident.model_dump(by_alias=True))
    return incident


