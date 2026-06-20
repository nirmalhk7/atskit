"""Portal metadata persistence (portal_entries table only)."""

from __future__ import annotations

import sqlite3
import threading
from datetime import date
from pathlib import Path
from typing import Iterable

from .models import PortalEntry
from .registry import SUPPORTED_PORTALS


class PortalStore:
    """SQLite store for portal_entries. Caller supplies the DB file path."""

    def __init__(self, db_path: Path | str) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS portal_entries (
                    name TEXT PRIMARY KEY,
                    slug TEXT NOT NULL,
                    portal TEXT NOT NULL,
                    sample_url TEXT NOT NULL,
                    updated_on TEXT NOT NULL,
                    last_scanned_date TEXT NOT NULL DEFAULT '',
                    status INTEGER NOT NULL DEFAULT 1
                )
                """
            )
        self._migrate_columns()

    def _migrate_columns(self) -> None:
        if not self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'portal_entries'"
        ).fetchone():
            return
        columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(portal_entries)").fetchall()
        }
        with self._conn:
            if "last_scanned_date" not in columns:
                self._conn.execute(
                    "ALTER TABLE portal_entries ADD COLUMN last_scanned_date TEXT NOT NULL DEFAULT ''"
                )
            if "status" not in columns:
                self._conn.execute(
                    "ALTER TABLE portal_entries ADD COLUMN status INTEGER NOT NULL DEFAULT 1"
                )

    def load(self) -> list[PortalEntry]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT name, slug, portal, sample_url, last_scanned_date, status
                FROM portal_entries
                ORDER BY lower(name), name
                """
            ).fetchall()
            return [
                PortalEntry(
                    name=row["name"],
                    slug=row["slug"],
                    portal=row["portal"],
                    sample_url=row["sample_url"],
                    last_scanned_date=row["last_scanned_date"] or "",
                    status=bool(row["status"] if row["status"] is not None else 1),
                )
                for row in rows
            ]

    def replace(self, entries: Iterable[PortalEntry]) -> None:
        with self._lock, self._conn:
            existing_dates = {
                row["name"]: row["last_scanned_date"]
                for row in self._conn.execute(
                    "SELECT name, last_scanned_date FROM portal_entries"
                ).fetchall()
            }
            self._conn.execute("DELETE FROM portal_entries")
            updated_on = date.today().isoformat()
            for entry in entries:
                if entry.portal not in SUPPORTED_PORTALS:
                    continue
                if not entry.name or not entry.slug:
                    continue
                last_scanned = existing_dates.get(entry.name, entry.last_scanned_date)
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO portal_entries(
                        name, slug, portal, sample_url, updated_on, last_scanned_date, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.name,
                        entry.slug,
                        entry.portal,
                        entry.sample_url,
                        updated_on,
                        last_scanned,
                        1 if entry.status else 0,
                    ),
                )

    def mark_scanned_today(self, name: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE portal_entries SET last_scanned_date = ? WHERE name = ?",
                (date.today().isoformat(), name),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
