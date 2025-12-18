# Decisions (MVP heuristics)

This project is intentionally a **portfolio MVP**: small enough to understand end-to-end, but opinionated enough to demonstrate real triage thinking.

## Correlation

- **Primary grouping**: `service + env`.
- **Time window**: if an existing incident for the same `service/env` was updated within the last ~60 minutes, new alerts attach to it.
- **De-dupe**: fingerprints are ignored for ~120 seconds to avoid repeated webhooks inflating the incident.

This is deliberately simple; in production you'd also correlate by deployment version, region/AZ, dependency graph, and trace/span attributes.

## Signal interpretation

Each normalized alert is mapped into one of:

- `saturation` (CPU/utilization/pools/capacity)
- `latency` (p95/p99/SLO breach)
- `errors` (5xx/exceptions/error-rate)
- `other`

If the alert includes numeric `observed` + `threshold`, we compute the state deterministically:

- `critical`: \(observed \ge threshold\)
- `warning`: \(observed \ge threshold * ratio\)
- `ok`: otherwise

Where `ratio` is slightly more sensitive for saturation (warn earlier) than for other signals.

## Impact rules (the “point” of the demo)

### Why saturation alone is not an incident

High saturation is often an **early warning**, not proof of user impact. If latency and errors remain normal, users may not notice anything yet (e.g., headroom is low but the system is still meeting SLOs).

So the MVP rule is:

- **Saturation critical + latency ok + errors ok ⇒ impact = none** (classification `capacity_warning`, status `watch`)

### When we *do* declare an incident

- **Errors critical OR latency critical ⇒ impact = major** (likely user-facing)
- **Saturation critical + (latency/errors warning or trending up) ⇒ impact = minor** (possible degradation)
- Warning-only errors/latency ⇒ `minor` and “investigate”

## Limitations

- In-memory incident store (no persistence)
- No true dependency graph or topology-aware correlation
- Sample provider payloads are “shaped like” real ones, but simplified

