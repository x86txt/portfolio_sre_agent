from __future__ import annotations

from typing import Any, Dict

from app.triage.models import Incident
from app.triage.report.runbook import suggest_runbook_steps
from app.triage.utils import now_utc


def generate_report_object(incident: Incident) -> Dict[str, Any]:
    impact = incident.impact.model_dump(by_alias=True)

    signals = []
    for sig_type, snap in incident.signals.items():
        s = snap.model_dump(by_alias=True)
        # ensure signalType is always present (dict keys may be stringified)
        s["signalType"] = getattr(sig_type, "value", str(sig_type))
        signals.append(s)

    # Keep timeline short + high signal.
    recent = []
    for a in incident.alerts[-10:]:
        recent.append(
            {
                "receivedAt": a.received_at,
                "provider": a.provider.value,
                "severity": a.severity.value,
                "signalType": a.signal_type.value,
                "message": a.message,
                "observed": a.observed,
                "threshold": a.threshold,
                "unit": a.unit,
            }
        )

    summary = incident.impact.summary or ""

    return {
        "incidentId": incident.id,
        "service": incident.service,
        "env": incident.env,
        "status": incident.status.value,
        "generatedAt": now_utc(),
        "impact": impact,
        "summary": summary,
        "signals": signals,
        "recentAlerts": recent,
        "runbook": suggest_runbook_steps(incident.impact.classification),
    }


def generate_report(incident: Incident) -> Dict[str, Any]:
    # wrapper kept for future LLM integration
    return generate_report_object(incident)


