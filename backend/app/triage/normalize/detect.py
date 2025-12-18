from __future__ import annotations

from typing import Any

from app.triage.models import Provider


def detect_provider(payload: Any) -> Provider:
    if not isinstance(payload, dict):
        return Provider.generic

    # Prometheus Alertmanager webhook usually has an "alerts" list.
    if isinstance(payload.get("alerts"), list):
        return Provider.prometheus

    # Datadog monitor webhook commonly has event_type + alert_type.
    if "event_type" in payload and "alert_type" in payload:
        return Provider.datadog

    # BetterStack sample: we'll treat presence of "incident" as BetterStack-ish.
    if "incident" in payload or "betterstack" in payload.get("source", "").lower():
        return Provider.betterstack

    return Provider.generic


