from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.api.state import engine, events
from app.triage.models import Provider
from app.triage.normalize.normalize import normalize_payload
from app.triage.scenarios.builtins import get_scenario

router = APIRouter()


@router.post("/scenarios/{scenario}")
def run_scenario(scenario: str) -> Dict[str, Any]:
    try:
        items: List[Dict[str, Any]] = get_scenario(scenario)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown scenario")

    incident_ids: list[str] = []
    events_ingested = 0

    for item in items:
        provider_raw = item.get("provider")
        payload = item.get("payload")

        provider: Provider | None = None
        if isinstance(provider_raw, str) and provider_raw:
            v = provider_raw.strip().lower()
            for p in Provider:
                if p.value == v:
                    provider = p
                    break

        alert_events = normalize_payload(provider=provider, payload=payload)
        for ev in alert_events:
            inc = engine.ingest_event(ev)
            incident_ids.append(inc.id)
            events_ingested += 1
            events.publish(event="alert_ingested", data={"incidentId": inc.id, "service": inc.service, "env": inc.env})
            events.publish(event="incident_updated", data=inc.model_dump(by_alias=True))

    # return last incident id for convenience
    last_id = incident_ids[-1] if incident_ids else None
    return {"scenario": scenario, "incidentIds": list(dict.fromkeys(incident_ids)), "eventsIngested": events_ingested, "lastIncidentId": last_id}


