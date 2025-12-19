from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Cache TTL: 1 hour (reports are cached until incident changes)
CACHE_TTL_SECONDS = 3600


class ReportCache:
    """
    SQLite-based cache for LLM-generated reports.

    Stores cached reports in a local SQLite database.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._db_path: Optional[Path] = None
        self._initialized = False

    def _get_db_path(self) -> Path:
        """Get the SQLite database path."""
        if self._db_path is not None:
            return self._db_path

        # Use environment variable or default to backend directory
        db_dir = os.getenv("CACHE_DB_DIR", "backend")
        db_path = Path(db_dir) / "cache.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        return db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get a SQLite connection with proper settings."""
        db_path = self._get_db_path()
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL for better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and performance
        return conn

    def _ensure_table(self) -> None:
        """Create the cache table if it doesn't exist."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            try:
                conn = self._get_connection()
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS report_cache (
                        incident_id TEXT NOT NULL,
                        model TEXT NOT NULL,
                        format TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (incident_id, model, format)
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_incident_id ON report_cache(incident_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_created_at ON report_cache(created_at)"
                )
                conn.commit()
                conn.close()
                self._initialized = True
            except Exception:
                # If we can't create the table, cache will be disabled
                pass

    def get(self, incident_id: str, model: str, format: str) -> Optional[str]:
        """
        Retrieve a cached report.

        Returns None if not found, expired, or SQLite is unavailable.
        """
        self._ensure_table()

        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT content, created_at FROM report_cache
                WHERE incident_id = ? AND model = ? AND format = ?
                """,
                (incident_id, model, format),
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            content, created_at_str = row
            created_at = datetime.fromisoformat(created_at_str)

            # Check if cache entry has expired
            if datetime.now() - created_at > timedelta(seconds=CACHE_TTL_SECONDS):
                # Expired - delete it and return None
                self._delete_entry(incident_id, model, format)
                return None

            return content
        except Exception:
            # SQLite unavailable or error - cache disabled
            return None

    def set(self, incident_id: str, model: str, format: str, content: str) -> bool:
        """
        Cache a report.

        Returns True if successful, False if SQLite is unavailable.
        """
        self._ensure_table()

        try:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO report_cache (incident_id, model, format, content, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (incident_id, model, format, content),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            # SQLite unavailable or error - cache disabled
            return False

    def _delete_entry(self, incident_id: str, model: str, format: str) -> None:
        """Delete a specific cache entry."""
        try:
            conn = self._get_connection()
            conn.execute(
                """
                DELETE FROM report_cache
                WHERE incident_id = ? AND model = ? AND format = ?
                """,
                (incident_id, model, format),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def invalidate_incident(self, incident_id: str) -> bool:
        """
        Invalidate all cached reports for an incident.

        Returns True if successful, False if SQLite is unavailable.
        """
        self._ensure_table()

        try:
            conn = self._get_connection()
            conn.execute(
                "DELETE FROM report_cache WHERE incident_id = ?",
                (incident_id,),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            # SQLite unavailable or error
            return False

    def cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        self._ensure_table()

        try:
            conn = self._get_connection()
            cutoff = datetime.now() - timedelta(seconds=CACHE_TTL_SECONDS)
            conn.execute(
                "DELETE FROM report_cache WHERE created_at < ?",
                (cutoff.isoformat(),),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def is_available(self) -> bool:
        """Check if SQLite cache is available."""
        try:
            self._ensure_table()
            return self._initialized
        except Exception:
            return False


# Global cache instance
cache = ReportCache()

