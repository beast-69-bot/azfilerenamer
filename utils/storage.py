"""
SQLite-backed user storage for the bot.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def _utc_now() -> str:
    """Return the current UTC time as an ISO string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class UserStore:
    """Persist bot users, roles, and metrics."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_premium INTEGER NOT NULL DEFAULT 0,
                    premium_since TEXT,
                    is_banned INTEGER NOT NULL DEFAULT 0,
                    banned_at TEXT,
                    joined_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    archives_processed INTEGER NOT NULL DEFAULT 0,
                    files_uploaded INTEGER NOT NULL DEFAULT 0,
                    zip_exports INTEGER NOT NULL DEFAULT 0,
                    last_archive_name TEXT
                )
                """
            )

    def upsert_user(self, telegram_user) -> sqlite3.Row:
        """Insert or update a user from Telegram metadata."""
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    user_id,
                    username,
                    first_name,
                    last_name,
                    joined_at,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    telegram_user.id,
                    telegram_user.username,
                    telegram_user.first_name,
                    telegram_user.last_name,
                    now,
                    now,
                ),
            )
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (telegram_user.id,),
            ).fetchone()

    def ensure_user_id(self, user_id: int) -> sqlite3.Row:
        """Create a placeholder user record if one does not exist yet."""
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, first_name, joined_at, last_seen_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (user_id, "Unknown User", now, now),
            )
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        """Fetch a single user record."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

    def set_premium(self, user_id: int, enabled: bool) -> sqlite3.Row:
        """Set or unset premium status."""
        self.ensure_user_id(user_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET is_premium = ?,
                    premium_since = ?
                WHERE user_id = ?
                """,
                (1 if enabled else 0, _utc_now() if enabled else None, user_id),
            )
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

    def set_banned(self, user_id: int, enabled: bool) -> sqlite3.Row:
        """Set or unset ban status."""
        self.ensure_user_id(user_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET is_banned = ?,
                    banned_at = ?
                WHERE user_id = ?
                """,
                (1 if enabled else 0, _utc_now() if enabled else None, user_id),
            )
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

    def increment_usage(
        self,
        user_id: int,
        archives_processed: int = 0,
        files_uploaded: int = 0,
        zip_exports: int = 0,
        last_archive_name: str | None = None,
    ) -> None:
        """Increment user counters after successful actions."""
        self.ensure_user_id(user_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET archives_processed = archives_processed + ?,
                    files_uploaded = files_uploaded + ?,
                    zip_exports = zip_exports + ?,
                    last_archive_name = COALESCE(?, last_archive_name),
                    last_seen_at = ?
                WHERE user_id = ?
                """,
                (
                    archives_processed,
                    files_uploaded,
                    zip_exports,
                    last_archive_name,
                    _utc_now(),
                    user_id,
                ),
            )

    def get_stats(self) -> sqlite3.Row:
        """Return aggregate bot statistics."""
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT
                    COUNT(*) AS total_users,
                    SUM(CASE WHEN is_premium = 1 THEN 1 ELSE 0 END) AS premium_users,
                    SUM(CASE WHEN is_banned = 1 THEN 1 ELSE 0 END) AS banned_users,
                    SUM(archives_processed) AS archives_processed,
                    SUM(files_uploaded) AS files_uploaded,
                    SUM(zip_exports) AS zip_exports
                FROM users
                """
            ).fetchone()

    def list_broadcast_targets(self) -> list[int]:
        """Return users eligible for bot broadcasts."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT user_id
                FROM users
                WHERE is_banned = 0
                ORDER BY joined_at ASC
                """
            ).fetchall()
        return [row["user_id"] for row in rows]
