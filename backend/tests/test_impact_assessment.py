from __future__ import annotations

from app.triage.correlation.engine import CorrelationEngine
from app.triage.models import ImpactLevel
from app.triage.normalize.normalize import normalize_payload
from app.triage.scenarios.builtins import full_outage, saturation_only
from app.triage.store.memory import MemoryIncidentStore


def _run_items(items):
    store = MemoryIncidentStore()
    engine = CorrelationEngine(store=store)
    last = None
    for item in items:
        events = normalize_payload(provider=None, payload=item["payload"])
        for ev in events:
            last = engine.ingest_event(ev)
    assert last is not None
    return last


def test_saturation_only_is_capacity_warning_not_incident():
    inc = _run_items(saturation_only())
    assert inc.impact.impact == ImpactLevel.none
    assert inc.impact.classification == "capacity_warning"


def test_full_outage_is_major():
    inc = _run_items(full_outage())
    assert inc.impact.impact == ImpactLevel.major
    assert inc.impact.classification in ("outage", "error_spike", "latency_degradation")


