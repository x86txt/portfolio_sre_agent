from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from app.triage.models import Incident, IncidentStatus
from app.triage.utils import now_utc


@dataclass
class MemoryIncidentStore:
    """
    Simple in-memory incident store.

    This is intentionally lightweight for a portfolio MVP. The rest of the code
    treats the store as an abstraction so it can be swapped for SQLite later.
    """

    incidents: Dict[str, Incident] = field(default_factory=dict)
    service_env_index: Dict[Tuple[str, str], List[str]] = field(default_factory=dict)
    dedupe_cache: Dict[str, datetime] = field(default_factory=dict)

    def upsert(self, incident: Incident) -> None:
        self.incidents[incident.id] = incident
        key = (incident.service, incident.env)
        ids = self.service_env_index.setdefault(key, [])
        if incident.id not in ids:
            ids.append(incident.id)

    def get(self, incident_id: str) -> Incident | None:
        return self.incidents.get(incident_id)

    def list(self, *, limit: int = 100) -> List[Incident]:
        items = sorted(self.incidents.values(), key=lambda i: i.updated_at, reverse=True)
        return items[:limit]

    def find_open(self, *, service: str, env: str, within: timedelta) -> Incident | None:
        key = (service, env)
        candidates = [self.incidents[iid] for iid in self.service_env_index.get(key, []) if iid in self.incidents]
        cutoff = now_utc() - within
        candidates = [
            inc
            for inc in candidates
            if inc.status != IncidentStatus.resolved and inc.updated_at >= cutoff
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda inc: inc.updated_at)

    def seen_recently(self, *, incident_id: str, fingerprint: str, within: timedelta) -> bool:
        key = f"{incident_id}:{fingerprint}"
        last = self.dedupe_cache.get(key)
        if not last:
            return False
        return (now_utc() - last) <= within

    def mark_seen(self, *, incident_id: str, fingerprint: str) -> None:
        key = f"{incident_id}:{fingerprint}"
        self.dedupe_cache[key] = now_utc()


