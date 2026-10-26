"""SQLite connection helper with WAL and foreign keys."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    service TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    sample_message TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incidents_fingerprint_status
    ON incidents(fingerprint, status);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(service);

CREATE TABLE IF NOT EXISTS fingerprint_events (
    fingerprint TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    level TEXT NOT NULL,
    service TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fp_events_fp_seen
    ON fingerprint_events(fingerprint, seen_at);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        # check_same_thread=False so FastAPI sync deps can share the factory pattern safely
        # per-request; callers should not share a single Connection across threads.
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()
