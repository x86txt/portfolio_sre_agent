from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from app.triage.models import AlertEvent, Provider, Severity, SignalType
from app.triage.normalize.detect import detect_provider
from app.triage.utils import now_utc, parse_datetime, stable_fingerprint


def _parse_severity(value: Any) -> Severity:
    if not value:
        return Severity.warning
    s = str(value).strip().lower()
    if s in ("critical", "crit", "page", "p1", "high"):
        return Severity.critical
    if s in ("warning", "warn", "p2", "medium"):
        return Severity.warning
    return Severity.info


def _infer_signal_type(name: str | None, *, labels: Dict[str, str], annotations: Dict[str, str]) -> SignalType:
    explicit = (
        labels.get("signal")
        or labels.get("signal_type")
        or annotations.get("signal")
        or annotations.get("signal_type")
    )
    if explicit:
        s = explicit.strip().lower()
        if "satur" in s or s in ("cpu", "pool", "capacity"):
            return SignalType.saturation
        if "lat" in s or "p99" in s or "p95" in s or "slo" in s:
            return SignalType.latency
        if "err" in s or "5xx" in s:
            return SignalType.errors

    blob = (name or "").lower()
    if any(tok in blob for tok in ("satur", "cpu", "pool", "capacity", "utilization", "exhaust")):
        return SignalType.saturation
    if any(tok in blob for tok in ("latency", "p99", "p95", "duration", "slow")):
        return SignalType.latency
    if any(tok in blob for tok in ("error", "errors", "5xx", "exception", "fault")):
        return SignalType.errors
    return SignalType.other


def _extract_service_env(*, labels: Dict[str, str], tags: List[str] | None = None) -> tuple[str, str]:
    service = (
        labels.get("service")
        or labels.get("app")
        or labels.get("job")
        or labels.get("component")
        or "unknown"
    )
    env = labels.get("env") or labels.get("environment") or "prod"

    if tags:
        for t in tags:
            if ":" not in t:
                continue
            k, v = t.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if k == "service" and service == "unknown":
                service = v
            if k in ("env", "environment"):
                env = v

    return service, env


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_prometheus(payload: Dict[str, Any]) -> List[AlertEvent]:
    out: List[AlertEvent] = []
    for a in payload.get("alerts", []) or []:
        labels = {str(k): str(v) for k, v in (a.get("labels") or {}).items()}
        annotations = {str(k): str(v) for k, v in (a.get("annotations") or {}).items()}

        service, env = _extract_service_env(labels=labels)
        name = labels.get("alertname") or annotations.get("title") or "prometheus_alert"
        signal_type = _infer_signal_type(name, labels=labels, annotations=annotations)

        observed = _parse_float(annotations.get("observed") or labels.get("observed"))
        threshold = _parse_float(annotations.get("threshold") or labels.get("threshold"))
        unit = annotations.get("unit") or labels.get("unit")

        severity = _parse_severity(labels.get("severity") or annotations.get("severity"))

        fingerprint = stable_fingerprint(
            "prometheus",
            service,
            env,
            signal_type.value,
            labels.get("alertname", ""),
            labels.get("instance", ""),
        )

        out.append(
            AlertEvent(
                id=str(uuid4()),
                provider=Provider.prometheus,
                received_at=now_utc(),
                starts_at=parse_datetime(a.get("startsAt")),
                ends_at=parse_datetime(a.get("endsAt")),
                service=service,
                env=env,
                severity=severity,
                signal_type=signal_type,
                metric=labels.get("metric") or annotations.get("metric"),
                observed=observed,
                threshold=threshold,
                unit=unit,
                message=annotations.get("summary") or annotations.get("description") or name,
                labels=labels,
                annotations=annotations,
                fingerprint=fingerprint,
                source_url=a.get("generatorURL"),
                raw=a,
            )
        )
    return out


def normalize_datadog(payload: Dict[str, Any]) -> List[AlertEvent]:
    tags = payload.get("tags") or []
    if not isinstance(tags, list):
        tags = []

    title = payload.get("title") or payload.get("event_title") or "datadog_alert"
    text = payload.get("text") or payload.get("message") or ""

    labels: Dict[str, str] = {"title": str(title)}
    annotations: Dict[str, str] = {"text": str(text)}

    service, env = _extract_service_env(labels={}, tags=[str(t) for t in tags])
    signal_type = _infer_signal_type(str(title), labels=labels, annotations=annotations)

    observed = _parse_float(payload.get("observed"))
    threshold = _parse_float(payload.get("threshold"))
    unit = payload.get("unit")

    severity = _parse_severity(payload.get("alert_type") or payload.get("severity"))

    fingerprint = stable_fingerprint(
        "datadog",
        service,
        env,
        signal_type.value,
        str(payload.get("id") or ""),
        str(title),
    )

    return [
        AlertEvent(
            id=str(uuid4()),
            provider=Provider.datadog,
            received_at=now_utc(),
            starts_at=parse_datetime(payload.get("date") or payload.get("triggered_at")),
            service=service,
            env=env,
            severity=severity,
            signal_type=signal_type,
            metric=payload.get("metric"),
            observed=observed,
            threshold=threshold,
            unit=str(unit) if unit else None,
            message=str(title),
            labels=labels,
            annotations=annotations,
            fingerprint=fingerprint,
            source_url=payload.get("url"),
            raw=payload,
        )
    ]


def normalize_betterstack(payload: Dict[str, Any]) -> List[AlertEvent]:
    incident = payload.get("incident") if isinstance(payload.get("incident"), dict) else payload
    labels: Dict[str, str] = {str(k): str(v) for k, v in (incident.get("labels") or {}).items()}
    annotations: Dict[str, str] = {str(k): str(v) for k, v in (incident.get("annotations") or {}).items()}

    # BetterStack-like payloads are not standardized for this portfolio MVP.
    service = incident.get("service") or labels.get("service") or "unknown"
    env = incident.get("env") or labels.get("env") or "prod"
    title = incident.get("name") or incident.get("title") or "betterstack_incident"

    signal_type = _infer_signal_type(str(title), labels=labels, annotations=annotations)

    observed = _parse_float(incident.get("observed") or annotations.get("observed"))
    threshold = _parse_float(incident.get("threshold") or annotations.get("threshold"))
    unit = incident.get("unit") or annotations.get("unit")

    severity = _parse_severity(incident.get("severity") or incident.get("status"))

    fingerprint = stable_fingerprint(
        "betterstack",
        str(service),
        str(env),
        signal_type.value,
        str(incident.get("id") or ""),
        str(title),
    )

    return [
        AlertEvent(
            id=str(uuid4()),
            provider=Provider.betterstack,
            received_at=now_utc(),
            starts_at=parse_datetime(incident.get("started_at") or incident.get("startedAt")),
            ends_at=parse_datetime(incident.get("ended_at") or incident.get("endedAt")),
            service=str(service),
            env=str(env),
            severity=severity,
            signal_type=signal_type,
            metric=incident.get("metric"),
            observed=observed,
            threshold=threshold,
            unit=str(unit) if unit else None,
            message=str(title),
            labels=labels,
            annotations=annotations,
            fingerprint=fingerprint,
            source_url=incident.get("url"),
            raw=payload,
        )
    ]


def normalize_payload(*, provider: Provider | None, payload: Any) -> List[AlertEvent]:
    if provider is None:
        provider = detect_provider(payload)

    if not isinstance(payload, dict):
        return []

    if provider == Provider.prometheus:
        return normalize_prometheus(payload)
    if provider == Provider.datadog:
        return normalize_datadog(payload)
    if provider == Provider.betterstack:
        return normalize_betterstack(payload)

    # Generic: treat as a single event if it looks close enough.
    service = str(payload.get("service") or "unknown")
    env = str(payload.get("env") or "prod")
    name = str(payload.get("name") or payload.get("title") or "generic_alert")
    labels = {str(k): str(v) for k, v in (payload.get("labels") or {}).items()} if isinstance(payload.get("labels"), dict) else {}
    annotations = {str(k): str(v) for k, v in (payload.get("annotations") or {}).items()} if isinstance(payload.get("annotations"), dict) else {}
    signal_type = _infer_signal_type(name, labels=labels, annotations=annotations)
    severity = _parse_severity(payload.get("severity"))

    fingerprint = stable_fingerprint("generic", service, env, signal_type.value, name)
    return [
        AlertEvent(
            id=str(uuid4()),
            provider=Provider.generic,
            received_at=now_utc(),
            starts_at=parse_datetime(payload.get("starts_at") or payload.get("startsAt")),
            ends_at=parse_datetime(payload.get("ends_at") or payload.get("endsAt")),
            service=service,
            env=env,
            severity=severity,
            signal_type=signal_type,
            metric=payload.get("metric"),
            observed=_parse_float(payload.get("observed")),
            threshold=_parse_float(payload.get("threshold")),
            unit=payload.get("unit"),
            message=name,
            labels=labels,
            annotations=annotations,
            fingerprint=fingerprint,
            raw=payload,
        )
    ]


