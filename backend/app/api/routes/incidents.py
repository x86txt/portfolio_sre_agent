from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.api.state import store
from app.triage.models import Incident, IncidentSummary

router = APIRouter()


@router.get("/incidents", response_model=List[IncidentSummary])
def list_incidents(limit: int = Query(default=50, ge=1, le=500)) -> List[IncidentSummary]:
    incidents = store.list(limit=limit)
    return [
        IncidentSummary(
            id=i.id,
            service=i.service,
            env=i.env,
            status=i.status,
            updated_at=i.updated_at,
            impact=i.impact,
            signals=i.signals,
        )
        for i in incidents
    ]


@router.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: str) -> Incident:
    incident = store.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


