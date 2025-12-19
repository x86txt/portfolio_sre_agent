from __future__ import annotations

import json
import os
from typing import Any, Optional

import redis
from redis.exceptions import ConnectionError, RedisError

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Cache TTL: 1 hour (reports are cached until incident changes)
CACHE_TTL_SECONDS = 3600


class ReportCache:
    """
    Redis-based cache for LLM-generated reports.

    Cache keys: report:{incident_id}:{model}:{format}
    """

    def __init__(self) -> None:
        self._client: Optional[redis.Redis[str]] = None
        self._connected = False

    def _get_client(self) -> Optional[redis.Redis[str]]:
        """Lazy initialization of Redis client."""
        if self._client is not None:
            return self._client

        try:
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,  # Return strings instead of bytes
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self._client.ping()
            self._connected = True
            return self._client
        except (ConnectionError, RedisError, OSError):
            # Redis not available - cache will be disabled
            self._connected = False
            return None

    def get(self, incident_id: str, model: str, format: str) -> Optional[str]:
        """
        Retrieve a cached report.

        Returns None if not found or Redis is unavailable.
        """
        client = self._get_client()
        if not client:
            return None

        try:
            key = f"report:{incident_id}:{model}:{format}"
            value = client.get(key)
            return value
        except (ConnectionError, RedisError):
            self._connected = False
            return None

    def set(self, incident_id: str, model: str, format: str, content: str) -> bool:
        """
        Cache a report.

        Returns True if successful, False if Redis is unavailable.
        """
        client = self._get_client()
        if not client:
            return False

        try:
            key = f"report:{incident_id}:{model}:{format}"
            client.setex(key, CACHE_TTL_SECONDS, content)
            return True
        except (ConnectionError, RedisError):
            self._connected = False
            return False

    def invalidate_incident(self, incident_id: str) -> bool:
        """
        Invalidate all cached reports for an incident.

        Returns True if successful, False if Redis is unavailable.
        """
        client = self._get_client()
        if not client:
            return False

        try:
            # Find all keys matching the pattern
            pattern = f"report:{incident_id}:*"
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
            return True
        except (ConnectionError, RedisError):
            self._connected = False
            return False

    def is_available(self) -> bool:
        """Check if Redis is available."""
        client = self._get_client()
        return client is not None and self._connected


# Global cache instance
cache = ReportCache()

