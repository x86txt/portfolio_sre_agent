from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Set

from app.triage.correlation.engine import CorrelationConfig, CorrelationEngine
from app.triage.store.memory import MemoryIncidentStore


@dataclass
class EventBus:
    subscribers: Set[asyncio.Queue[str]] = field(default_factory=set)

    async def subscribe(self) -> AsyncIterator[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self.subscribers.add(q)
        try:
            # send an initial comment so clients connect immediately
            yield ": connected\n\n"
            while True:
                msg = await q.get()
                yield msg
        finally:
            self.subscribers.discard(q)

    def publish(self, *, event: str, data: Dict[str, Any]) -> None:
        payload = json.dumps(data, default=str)
        msg = f"event: {event}\ndata: {payload}\n\n"
        dead: list[asyncio.Queue[str]] = []
        for q in self.subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                # slow subscriber: drop it
                dead.append(q)
        for q in dead:
            self.subscribers.discard(q)


store = MemoryIncidentStore()
engine = CorrelationEngine(store=store, cfg=CorrelationConfig())
events = EventBus()


