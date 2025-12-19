from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Rate limit: 3 LLM API calls per hour per IP
RATE_LIMIT_REQUESTS = 3
RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour


class RateLimiter:
    """
    SQLite-based rate limiter for LLM API calls.
    
    Tracks requests per IP address and enforces a limit of 3 requests per hour.
    The limit is shared across all LLM providers (OpenAI + Anthropic combined).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._db_path: Optional[Path] = None
        self._initialized = False

    def _get_db_path(self) -> Path:
        """Get the SQLite database path (reuse cache DB directory)."""
        if self._db_path is not None:
            return self._db_path

        # Use the same directory as cache, but separate database file
        db_dir = os.getenv("CACHE_DB_DIR", "backend")
        db_path = Path(db_dir) / "rate_limit.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        return db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get a SQLite connection with proper settings."""
        db_path = self._get_db_path()
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _ensure_table(self) -> None:
        """Create the rate limit table if it doesn't exist."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            try:
                conn = self._get_connection()
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_limits (
                        ip_address TEXT NOT NULL,
                        request_time TIMESTAMP NOT NULL,
                        PRIMARY KEY (ip_address, request_time)
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_ip_time ON rate_limits(ip_address, request_time)"
                )
                conn.commit()
                conn.close()
                self._initialized = True
            except Exception:
                # If we can't create the table, rate limiting will be disabled
                pass

    def check_rate_limit(self, ip_address: str) -> tuple[bool, Optional[int]]:
        """
        Check if the IP address has exceeded the rate limit.
        
        Returns:
            (allowed, remaining_requests) - True if allowed, False if rate limited.
            remaining_requests is None if rate limiting is unavailable.
        """
        self._ensure_table()

        try:
            conn = self._get_connection()
            
            # Calculate the cutoff time (1 hour ago)
            cutoff = datetime.now() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
            
            # Count requests in the last hour
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM rate_limits
                WHERE ip_address = ? AND request_time > ?
                """,
                (ip_address, cutoff.isoformat()),
            )
            count = cursor.fetchone()[0]
            
            # Check if limit exceeded
            allowed = count < RATE_LIMIT_REQUESTS
            remaining = max(0, RATE_LIMIT_REQUESTS - count)
            
            # If allowed, record this request
            if allowed:
                conn.execute(
                    """
                    INSERT INTO rate_limits (ip_address, request_time)
                    VALUES (?, CURRENT_TIMESTAMP)
                    """,
                    (ip_address,),
                )
                conn.commit()
            
            # Clean up old entries (older than 1 hour)
            conn.execute(
                "DELETE FROM rate_limits WHERE request_time < ?",
                (cutoff.isoformat(),),
            )
            conn.commit()
            
            conn.close()
            return (allowed, remaining)
        except Exception:
            # Rate limiting unavailable - allow the request
            return (True, None)

    def get_remaining_requests(self, ip_address: str) -> Optional[int]:
        """Get the number of remaining requests for an IP address."""
        self._ensure_table()

        try:
            conn = self._get_connection()
            cutoff = datetime.now() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
            
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM rate_limits
                WHERE ip_address = ? AND request_time > ?
                """,
                (ip_address, cutoff.isoformat()),
            )
            count = cursor.fetchone()[0]
            conn.close()
            
            return max(0, RATE_LIMIT_REQUESTS - count)
        except Exception:
            return None

    def unblock_ip(self, ip_address: str) -> bool:
        """
        Remove all rate limit entries for an IP address (unblock/reset).
        
        Returns True if successful, False if rate limiting is unavailable.
        """
        self._ensure_table()

        try:
            conn = self._get_connection()
            conn.execute(
                "DELETE FROM rate_limits WHERE ip_address = ?",
                (ip_address,),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def is_available(self) -> bool:
        """Check if rate limiting is available."""
        try:
            self._ensure_table()
            return self._initialized
        except Exception:
            return False


# Global rate limiter instance
rate_limiter = RateLimiter()

