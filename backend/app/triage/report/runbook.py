from __future__ import annotations

from typing import Any, Dict, List


def suggest_runbook_steps(classification: str) -> List[Dict[str, Any]]:
    """
    Deterministic runbook suggestions.

    For a portfolio MVP, we keep this generic + practical (Kubernetes-ish), and
    avoid vendor-specific commands.
    """

    if classification == "capacity_warning":
        return [
            {
                "title": "Validate whether capacity is actually impacting users",
                "verify": [
                    "Check p95/p99 latency against SLO (if you have it).",
                    "Check error rate (% 5xx / exceptions) for the same time window.",
                    "Confirm request rate / throughput is normal.",
                ],
            },
            {
                "title": "Identify the saturated resource",
                "verify": [
                    "CPU saturation: look for hot pods/nodes.",
                    "Connection pool saturation: inspect DB pool usage vs max.",
                    "Thread/worker saturation: check queue depth and worker utilization.",
                ],
                "exampleCommands": [
                    "kubectl top pods -n <ns>",
                    "kubectl top nodes",
                    "kubectl describe hpa -n <ns> <hpa-name>",
                ],
            },
            {
                "title": "Mitigate safely (if needed)",
                "mitigate": [
                    "Scale out if autoscaling isn't keeping up (or temporarily raise limits).",
                    "Rollback the last deploy if the change increased resource usage.",
                    "Apply rate limiting / shed non-critical traffic if you are nearing failure.",
                ],
            },
        ]

    if classification in ("latency_degradation", "degradation_possible"):
        return [
            {
                "title": "Confirm where latency is coming from",
                "verify": [
                    "Break down latency by dependency (DB, cache, external APIs).",
                    "Compare p95 vs p99 — tail latency often points to contention.",
                    "Check saturation and error rate in the same window.",
                ],
            },
            {
                "title": "Mitigate",
                "mitigate": [
                    "Scale the bottleneck (pods, DB, cache) or reduce concurrency.",
                    "Disable non-critical features / expensive code paths.",
                    "Rollback or pause a deployment if it correlates with the regression.",
                ],
            },
            {
                "title": "Validate recovery",
                "confirm": [
                    "Latency back within SLO for 10–15 minutes.",
                    "Error rate stable.",
                    "Saturation trends downward.",
                ],
            },
        ]

    if classification in ("error_spike", "outage"):
        return [
            {
                "title": "Stop the bleeding",
                "mitigate": [
                    "Rollback the most recent deploy if errors started immediately after it.",
                    "Scale if errors are from timeouts/resource exhaustion.",
                    "Enable a safe-mode / fallback (if available) to reduce blast radius.",
                ],
            },
            {
                "title": "Triage the errors quickly",
                "verify": [
                    "Look at error logs / traces: top exception types, top endpoints.",
                    "Check dependency health (DB, cache, downstream APIs).",
                    "Check if errors are limited to a single AZ/region/version.",
                ],
            },
            {
                "title": "Validate recovery",
                "confirm": [
                    "Error rate back to baseline.",
                    "Latency stable.",
                    "No new alerts firing for 10–15 minutes.",
                ],
            },
        ]

    # Default: generic investigation.
    return [
        {
            "title": "Quick validation",
            "verify": [
                "Is there user impact? (latency, errors, synthetic checks)",
                "Is it isolated to one service/env/region?",
                "Did anything change recently? (deploys, config, traffic)",
            ],
        },
        {
            "title": "Next steps",
            "mitigate": [
                "Scale bottlenecks or reduce load.",
                "Rollback if the issue correlates with a recent change.",
                "Escalate to the owning team if needed.",
            ],
        },
    ]


