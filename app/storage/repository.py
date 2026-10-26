"""Incident and fingerprint-event persistence."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from app.models.schemas import (
    IncidentRead,
    IncidentStatus,
    Severity,
)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _row_to_incident(row: sqlite3.Row) -> IncidentRead:
    return IncidentRead(
        id=row["id"],
        fingerprint=row["fingerprint"],
        title=row["title"],
        severity=Severity(row["severity"]),
        status=IncidentStatus(row["status"]),
        service=row["service"],
        count=row["count"],
        sample_message=row["sample_message"],
        first_seen=_parse_dt(row["first_seen"]),
        last_seen=_parse_dt(row["last_seen"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


class IncidentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def record_event(
        self,
        fingerprint: str,
        *,
        seen_at: datetime,
        level: str,
        service: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO fingerprint_events (fingerprint, seen_at, level, service)
            VALUES (?, ?, ?, ?)
            """,
            (fingerprint, seen_at.isoformat(), level, service),
        )

    def count_in_window(
        self,
        fingerprint: str,
        *,
        window_seconds: int,
        now: datetime,
    ) -> int:
        since = (now - timedelta(seconds=window_seconds)).isoformat()
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS c FROM fingerprint_events
            WHERE fingerprint = ? AND seen_at >= ?
            """,
            (fingerprint, since),
        ).fetchone()
        return int(row["c"]) if row else 0

    def baseline_stats(
        self,
        fingerprint: str,
        *,
        window_seconds: int,
        now: datetime,
        lookback_windows: int = 12,
    ) -> tuple[float, int]:
        """Average event count per window over prior lookback_windows (excludes current)."""
        samples: list[int] = []
        for i in range(1, lookback_windows + 1):
            end = now - timedelta(seconds=window_seconds * i)
            start = end - timedelta(seconds=window_seconds)
            row = self.conn.execute(
                """
                SELECT COUNT(*) AS c FROM fingerprint_events
                WHERE fingerprint = ? AND seen_at >= ? AND seen_at < ?
                """,
                (fingerprint, start.isoformat(), end.isoformat()),
            ).fetchone()
            samples.append(int(row["c"]) if row else 0)
        total_events = sum(samples)
        avg = total_events / lookback_windows if lookback_windows else 0.0
        return avg, total_events

    def find_open_by_fingerprint(self, fingerprint: str) -> IncidentRead | None:
        row = self.conn.execute(
            """
            SELECT * FROM incidents
            WHERE fingerprint = ? AND status IN ('open', 'acknowledged')
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (fingerprint,),
        ).fetchone()
        return _row_to_incident(row) if row else None

    def create_incident(
        self,
        *,
        fingerprint: str,
        title: str,
        severity: Severity,
        service: str,
        count: int,
        sample_message: str,
        first_seen: datetime,
        last_seen: datetime,
    ) -> IncidentRead:
        now = datetime.now(UTC)
        incident_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO incidents (
                id, fingerprint, title, severity, status, service, count,
                sample_message, first_seen, last_seen, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                fingerprint,
                title,
                severity.value,
                IncidentStatus.OPEN.value,
                service,
                count,
                sample_message,
                first_seen.isoformat(),
                last_seen.isoformat(),
                now.isoformat(),
                now.isoformat(),
            ),
        )
        created = self.get_by_id(incident_id)
        assert created is not None
        return created

    def bump_incident(
        self,
        incident_id: str,
        *,
        count: int,
        last_seen: datetime,
        severity: Severity,
        sample_message: str,
        title: str,
    ) -> IncidentRead:
        now = datetime.now(UTC)
        self.conn.execute(
            """
            UPDATE incidents
            SET count = ?,
                last_seen = ?,
                severity = ?,
                sample_message = ?,
                title = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                count,
                last_seen.isoformat(),
                severity.value,
                sample_message,
                title,
                now.isoformat(),
                incident_id,
            ),
        )
        updated = self.get_by_id(incident_id)
        assert updated is not None
        return updated

    def get_by_id(self, incident_id: str) -> IncidentRead | None:
        row = self.conn.execute(
            "SELECT * FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()
        return _row_to_incident(row) if row else None

    def list_incidents(
        self,
        *,
        status: IncidentStatus | None = None,
        severity: Severity | None = None,
        service: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IncidentRead]:
        clauses: list[str] = []
        params: list[object] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity.value)
        if service is not None:
            clauses.append("service = ?")
            params.append(service)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        rows = self.conn.execute(
            f"""
            SELECT * FROM incidents
            {where}
            ORDER BY last_seen DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
        return [_row_to_incident(r) for r in rows]

    def update_status(
        self,
        incident_id: str,
        status: IncidentStatus,
    ) -> IncidentRead | None:
        existing = self.get_by_id(incident_id)
        if existing is None:
            return None
        now = datetime.now(UTC)
        self.conn.execute(
            """
            UPDATE incidents SET status = ?, updated_at = ? WHERE id = ?
            """,
            (status.value, now.isoformat(), incident_id),
        )
        return self.get_by_id(incident_id)
