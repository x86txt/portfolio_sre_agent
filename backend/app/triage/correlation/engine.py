from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from app.triage.correlation.impact import assess_incident, derive_status
from app.triage.models import (
    AlertEvent,
    ImpactLevel,
    Incident,
    SignalSnapshot,
    SignalState,
    SignalType,
    Trend,
)
from app.triage.store.memory import MemoryIncidentStore
from app.triage.utils import now_utc


@dataclass(frozen=True)
class CorrelationConfig:
    incident_window_minutes: int = 60
    dedupe_window_seconds: int = 120
    max_signal_history: int = 12

    saturation_warn_ratio: float = 0.9  # warn at 90% of threshold
    generic_warn_ratio: float = 0.95  # warn at 95% of threshold


def _compute_state(event: AlertEvent, *, cfg: CorrelationConfig) -> SignalState:
    # If we have no numeric context, fall back to provider severity.
    if event.observed is None or event.threshold is None:
        if event.severity.value == "critical":
            return SignalState.critical
        if event.severity.value == "warning":
            return SignalState.warning
        return SignalState.ok

    warn_ratio = cfg.saturation_warn_ratio if event.signal_type == SignalType.saturation else cfg.generic_warn_ratio
    if event.observed >= event.threshold:
        return SignalState.critical
    if event.observed >= event.threshold * warn_ratio:
        return SignalState.warning
    return SignalState.ok


def _compute_trend(history: list[float]) -> Trend:
    if len(history) < 3:
        return Trend.unknown
    a, b, c = history[-3], history[-2], history[-1]
    # small absolute tolerance; many of our signals are ratios (0..1) or percents.
    eps = 1e-6
    if c > b and b > a and (c - a) > eps:
        return Trend.up
    if c < b and b < a and (a - c) > eps:
        return Trend.down
    return Trend.flat


def _update_signal_snapshot(snapshot: SignalSnapshot | None, event: AlertEvent, *, cfg: CorrelationConfig) -> SignalSnapshot:
    state = _compute_state(event, cfg=cfg)
    history = list(snapshot.history) if snapshot else []
    if event.observed is not None:
        history.append(float(event.observed))
        if len(history) > cfg.max_signal_history:
            history = history[-cfg.max_signal_history :]
    trend = _compute_trend(history)

    return SignalSnapshot(
        signal_type=event.signal_type,
        state=state,
        trend=trend,
        observed=event.observed,
        threshold=event.threshold,
        unit=event.unit,
        last_updated_at=now_utc(),
        history=history,
    )


class CorrelationEngine:
    def __init__(self, *, store: MemoryIncidentStore, cfg: CorrelationConfig | None = None) -> None:
        self.store = store
        self.cfg = cfg or CorrelationConfig()

    def ingest_event(self, event: AlertEvent) -> Incident:
        window = timedelta(minutes=self.cfg.incident_window_minutes)
        incident = self.store.find_open(service=event.service, env=event.env, within=window)

        if not incident:
            incident = Incident(id=str(uuid4()), service=event.service, env=event.env)

        # lightweight dedupe
        if self.store.seen_recently(
            incident_id=incident.id,
            fingerprint=event.fingerprint,
            within=timedelta(seconds=self.cfg.dedupe_window_seconds),
        ):
            return incident

        self.store.mark_seen(incident_id=incident.id, fingerprint=event.fingerprint)

        incident.alerts.append(event)
        incident.updated_at = now_utc()

        snapshot = incident.signals.get(event.signal_type)
        incident.signals[event.signal_type] = _update_signal_snapshot(snapshot, event, cfg=self.cfg)

        prev_impact: ImpactLevel | None = incident.impact.impact if incident.impact else None
        impact = assess_incident(incident, previous_impact=prev_impact)
        incident.impact = impact
        incident.status = derive_status(impact=impact, incident=incident, previous_impact=prev_impact)

        self.store.upsert(incident)
        return incident

    def ingest(self, events: list[AlertEvent]) -> list[Incident]:
        updated: dict[str, Incident] = {}
        for ev in events:
            inc = self.ingest_event(ev)
            updated[inc.id] = inc
        return list(updated.values())


