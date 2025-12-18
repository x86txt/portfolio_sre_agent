from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def stable_fingerprint(*parts: str) -> str:
    joined = "|".join(p.strip() for p in parts if p is not None)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def parse_datetime(value: Any) -> datetime | None:
    """
    Best-effort datetime parsing for sample provider payloads.

    Supports:
    - ISO8601 strings (with or without 'Z')
    - epoch seconds / millis (int/float)
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # heuristically treat > 10^12 as ms
        seconds = float(value) / 1000.0 if value > 1_000_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds, tz=timezone.utc)

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    return None


