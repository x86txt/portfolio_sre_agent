from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

from app.triage.utils import now_utc


def _iso(dt) -> str:
    return dt.isoformat()


def saturation_only(service: str = "checkout", env: str = "prod") -> List[Dict[str, Any]]:
    """
    Scenario: saturation is 100%, but latency/errors are normal.
    Expectation: impact=none, status=watch (capacity warning).
    """
    t = now_utc()

    return [
        {
            "provider": "prometheus",
            "payload": {
                "receiver": "aitriage",
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {
                            "alertname": "ServiceSaturationHigh",
                            "service": service,
                            "env": env,
                            "severity": "critical",
                            "metric": "cpu_utilization",
                        },
                        "annotations": {
                            "summary": "CPU saturation is extremely high.",
                            "observed": 100,
                            "threshold": 95,
                            "unit": "%",
                            "signal_type": "saturation",
                        },
                        "startsAt": _iso(t - timedelta(minutes=3)),
                        "endsAt": _iso(t + timedelta(minutes=30)),
                        "generatorURL": "https://prometheus.example/graph",
                    }
                ],
            },
        },
        {
            "provider": "datadog",
            "payload": {
                "event_type": "monitor_alert",
                "alert_type": "info",
                "title": f"{service}: p99 latency within SLO",
                "text": "Latency is stable and within SLO.",
                "tags": [f"service:{service}", f"env:{env}"],
                "metric": "http_request_duration_p99",
                "observed": 180,
                "threshold": 400,
                "unit": "ms",
                "url": "https://app.datadoghq.com/monitors/123",
            },
        },
        {
            "provider": "betterstack",
            "payload": {
                "incident": {
                    "id": "bs-001",
                    "name": f"{service}: error rate normal",
                    "service": service,
                    "env": env,
                    "severity": "info",
                    "metric": "http_5xx_rate",
                    "observed": 0.2,
                    "threshold": 1.0,
                    "unit": "%",
                    "started_at": _iso(t - timedelta(minutes=2)),
                    "url": "https://betterstack.example/incidents/bs-001",
                    "labels": {"signal_type": "errors"},
                }
            },
        },
    ]


def full_outage(service: str = "checkout", env: str = "prod") -> List[Dict[str, Any]]:
    """
    Scenario: saturation is high AND latency/errors are critical.
    Expectation: impact=major, status=investigating.
    """
    t = now_utc()
    return [
        {
            "provider": "prometheus",
            "payload": {
                "receiver": "aitriage",
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {
                            "alertname": "ServiceErrorRateHigh",
                            "service": service,
                            "env": env,
                            "severity": "critical",
                            "metric": "http_5xx_rate",
                        },
                        "annotations": {
                            "summary": "5xx error rate is above SLO.",
                            "observed": 7.2,
                            "threshold": 1.0,
                            "unit": "%",
                            "signal_type": "errors",
                        },
                        "startsAt": _iso(t - timedelta(minutes=2)),
                        "endsAt": _iso(t + timedelta(minutes=30)),
                        "generatorURL": "https://prometheus.example/graph",
                    }
                ],
            },
        },
        {
            "provider": "datadog",
            "payload": {
                "event_type": "monitor_alert",
                "alert_type": "critical",
                "title": f"{service}: p99 latency high",
                "text": "Latency is above SLO.",
                "tags": [f"service:{service}", f"env:{env}"],
                "metric": "http_request_duration_p99",
                "observed": 1800,
                "threshold": 400,
                "unit": "ms",
                "url": "https://app.datadoghq.com/monitors/999",
            },
        },
        {
            "provider": "betterstack",
            "payload": {
                "incident": {
                    "id": "bs-999",
                    "name": f"{service}: saturation critical",
                    "service": service,
                    "env": env,
                    "severity": "critical",
                    "metric": "cpu_utilization",
                    "observed": 99.8,
                    "threshold": 95,
                    "unit": "%",
                    "started_at": _iso(t - timedelta(minutes=4)),
                    "url": "https://betterstack.example/incidents/bs-999",
                    "labels": {"signal_type": "saturation"},
                }
            },
        },
    ]


def get_scenario(name: str) -> List[Dict[str, Any]]:
    key = (name or "").strip().lower()
    if key in ("saturation_only", "saturation-only", "capacity_warning"):
        return saturation_only()
    if key in ("full_outage", "full-outage", "outage"):
        return full_outage()
    raise KeyError(f"Unknown scenario: {name}")


