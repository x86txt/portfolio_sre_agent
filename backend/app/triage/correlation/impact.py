from __future__ import annotations

from app.triage.models import (
    ImpactAssessment,
    ImpactLevel,
    Incident,
    IncidentStatus,
    SignalState,
    SignalType,
    Trend,
)


def assess_incident(incident: Incident, *, previous_impact: ImpactLevel | None = None) -> ImpactAssessment:
    """
    Deterministic impact assessment.

    Key behavior:
    - saturation==critical alone does NOT imply user impact if latency/errors are normal.
    """

    signals = incident.signals

    errors = signals.get(SignalType.errors)
    latency = signals.get(SignalType.latency)
    saturation = signals.get(SignalType.saturation)

    errors_state = errors.state if errors else SignalState.ok
    latency_state = latency.state if latency else SignalState.ok
    saturation_state = saturation.state if saturation else SignalState.ok

    errors_up = errors.trend == Trend.up if errors else False
    latency_up = latency.trend == Trend.up if latency else False

    reasons: list[str] = []

    # MAJOR: direct customer pain signals.
    if errors_state == SignalState.critical and latency_state == SignalState.critical:
        reasons.append("Errors and latency are both critical.")
        return ImpactAssessment(
            impact=ImpactLevel.major,
            confidence=0.9,
            classification="outage",
            summary="Likely user-facing outage: both errors and latency are critical.",
            reasons=reasons,
        )

    if errors_state == SignalState.critical:
        reasons.append("Errors are critical.")
        return ImpactAssessment(
            impact=ImpactLevel.major,
            confidence=0.8,
            classification="error_spike",
            summary="Likely user-facing issue: error rate is critical.",
            reasons=reasons,
        )

    if latency_state == SignalState.critical:
        reasons.append("Latency is critical.")
        return ImpactAssessment(
            impact=ImpactLevel.major,
            confidence=0.8,
            classification="latency_degradation",
            summary="Likely user-facing issue: latency is critical.",
            reasons=reasons,
        )

    # Saturation: interpret carefully with context.
    if saturation_state == SignalState.critical:
        if (
            errors_state in (SignalState.warning, SignalState.critical)
            or latency_state in (SignalState.warning, SignalState.critical)
            or errors_up
            or latency_up
        ):
            reasons.append("Saturation is critical and errors/latency indicate possible impact.")
            return ImpactAssessment(
                impact=ImpactLevel.minor,
                confidence=0.7,
                classification="degradation_possible",
                summary="Potential degradation: saturation is critical and other signals are worsening.",
                reasons=reasons,
            )

        reasons.append("Saturation is critical, but latency and errors are normal.")
        return ImpactAssessment(
            impact=ImpactLevel.none,
            confidence=0.65,
            classification="capacity_warning",
            summary="Capacity warning: saturation is high, but no evidence of user impact yet.",
            reasons=reasons,
        )

    # Minor: early warnings.
    if errors_state == SignalState.warning or latency_state == SignalState.warning:
        reasons.append("Latency/errors are warning-level.")
        return ImpactAssessment(
            impact=ImpactLevel.minor,
            confidence=0.6,
            classification="investigate",
            summary="Investigate: warning-level errors/latency without clear outage signals.",
            reasons=reasons,
        )

    return ImpactAssessment(
        impact=ImpactLevel.none,
        confidence=0.55,
        classification="healthy",
        summary="No clear incident signals. System appears healthy.",
        reasons=reasons,
    )


def derive_status(*, impact: ImpactAssessment, incident: Incident, previous_impact: ImpactLevel | None) -> IncidentStatus:
    """
    Map impact to an incident status with lightweight resolution logic.
    """
    # If we recovered from a real incident, mark resolved.
    if (
        impact.impact == ImpactLevel.none
        and previous_impact in (ImpactLevel.major, ImpactLevel.minor)
        and impact.classification == "healthy"
    ):
        return IncidentStatus.resolved

    if impact.impact in (ImpactLevel.major, ImpactLevel.minor):
        return IncidentStatus.investigating

    if impact.classification == "capacity_warning":
        return IncidentStatus.watch

    # Default: if we have any alerts at all, keep it watch; otherwise resolved.
    return IncidentStatus.watch if incident.alerts else IncidentStatus.resolved


