from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.triage.utils import now_utc, to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Provider(str, Enum):
    prometheus = "prometheus"
    datadog = "datadog"
    betterstack = "betterstack"
    generic = "generic"


class SignalType(str, Enum):
    saturation = "saturation"
    latency = "latency"
    errors = "errors"
    other = "other"


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class SignalState(str, Enum):
    ok = "ok"
    warning = "warning"
    critical = "critical"


class Trend(str, Enum):
    up = "up"
    down = "down"
    flat = "flat"
    unknown = "unknown"


class IncidentStatus(str, Enum):
    watch = "watch"
    investigating = "investigating"
    mitigating = "mitigating"
    resolved = "resolved"


class ImpactLevel(str, Enum):
    none = "none"
    minor = "minor"
    major = "major"


class ResolutionStatus(str, Enum):
    none = "none"
    resolved = "resolved"
    auto_closed = "auto_closed"
    false_alert = "false_alert"
    accepted = "accepted"  # accepted / won't fix


class AlertEvent(CamelModel):
    id: str
    provider: Provider
    received_at: datetime = Field(default_factory=now_utc)

    # provider-specific lifecycle (optional)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    service: str
    env: str = "prod"

    severity: Severity = Severity.warning
    signal_type: SignalType = SignalType.other

    metric: str | None = None
    observed: float | None = None
    threshold: float | None = None
    unit: str | None = None

    message: str | None = None

    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)

    fingerprint: str
    source_url: str | None = None

    # Useful for debugging/demoing. We keep it optional and exclude it from
    # schema examples in the UI.
    raw: dict[str, Any] | None = None


class SignalSnapshot(CamelModel):
    signal_type: SignalType
    state: SignalState
    trend: Trend = Trend.unknown

    observed: float | None = None
    threshold: float | None = None
    unit: str | None = None

    last_updated_at: datetime = Field(default_factory=now_utc)
    history: list[float] = Field(default_factory=list)


class ImpactAssessment(CamelModel):
    impact: ImpactLevel = ImpactLevel.none
    confidence: float = 0.5
    classification: str = "unknown"
    summary: str = ""
    reasons: list[str] = Field(default_factory=list)


class Incident(CamelModel):
    id: str
    service: str
    env: str

    status: IncidentStatus = IncidentStatus.watch
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    impact: ImpactAssessment = Field(default_factory=ImpactAssessment)
    signals: dict[SignalType, SignalSnapshot] = Field(default_factory=dict)
    alerts: list[AlertEvent] = Field(default_factory=list)
    resolution_status: ResolutionStatus = ResolutionStatus.none
    resolution_note: str | None = None


class IncidentSummary(CamelModel):
    id: str
    service: str
    env: str
    status: IncidentStatus
    updated_at: datetime
    impact: ImpactAssessment
    signals: dict[SignalType, SignalSnapshot] = Field(default_factory=dict)
    resolution_status: ResolutionStatus = ResolutionStatus.none


class ReportFormat(str, Enum):
    text = "text"
    markdown = "markdown"
    json = "json"


class LlmMode(str, Enum):
    auto = "auto"
    off = "off"
    openai = "openai"
    anthropic = "anthropic"


