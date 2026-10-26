"""Business orchestration — keeps routes and CLI thin."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.config import Settings
from app.detection.engine import DetectionEngine
from app.detection.fingerprint import fingerprint_for_log
from app.models.schemas import (
    IncidentRead,
    IncidentStatus,
    IngestResult,
    LogEntry,
    Severity,
)
from app.storage.repository import IncidentRepository

logger = logging.getLogger(__name__)


class IncidentService:
    def __init__(self, repo: IncidentRepository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings
        self.engine = DetectionEngine(
            repeat_threshold=settings.error_repeat_threshold,
            baseline_multiplier=settings.baseline_multiplier,
            baseline_min_samples=settings.baseline_min_samples,
        )

    def ingest(self, logs: list[LogEntry]) -> IngestResult:
        created_ids: list[str] = []
        updated_ids: list[str] = []
        created = 0
        updated = 0

        for entry in logs:
            now = entry.timestamp or datetime.now(UTC)
            if entry.timestamp is None:
                entry = entry.model_copy(update={"timestamp": now})

            fp = fingerprint_for_log(entry)
            self.repo.record_event(
                fp,
                seen_at=now,
                level=entry.level,
                service=entry.service,
            )

            window_count = self.repo.count_in_window(
                fp,
                window_seconds=self.settings.error_window_seconds,
                now=now,
            )
            baseline_avg, baseline_samples = self.repo.baseline_stats(
                fp,
                window_seconds=self.settings.error_window_seconds,
                now=now,
            )

            existing = self.repo.find_open_by_fingerprint(fp)
            first_seen = existing.first_seen if existing else now

            hit = self.engine.evaluate(
                entry,
                fp,
                window_count=window_count,
                baseline_avg=baseline_avg,
                baseline_samples=baseline_samples,
                first_seen=first_seen,
                last_seen=now,
            )
            if hit is None:
                continue

            if existing is not None:
                incident = self.repo.bump_incident(
                    existing.id,
                    count=hit.count,
                    last_seen=hit.last_seen,
                    severity=hit.severity,
                    sample_message=hit.sample_message,
                    title=hit.title,
                )
                updated += 1
                updated_ids.append(incident.id)
                logger.info(
                    "Updated incident %s fp=%s reason=%s",
                    incident.id,
                    fp,
                    hit.reason,
                )
            else:
                incident = self.repo.create_incident(
                    fingerprint=hit.fingerprint,
                    title=hit.title,
                    severity=hit.severity,
                    service=hit.service,
                    count=hit.count,
                    sample_message=hit.sample_message,
                    first_seen=hit.first_seen,
                    last_seen=hit.last_seen,
                )
                created += 1
                created_ids.append(incident.id)
                logger.info(
                    "Created incident %s fp=%s reason=%s",
                    incident.id,
                    fp,
                    hit.reason,
                )

        self.repo.conn.commit()
        return IngestResult(
            accepted=len(logs),
            incidents_created=created,
            incidents_updated=updated,
            incident_ids=created_ids + updated_ids,
        )

    def list_incidents(
        self,
        *,
        status: IncidentStatus | None = None,
        severity: Severity | None = None,
        service: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IncidentRead]:
        return self.repo.list_incidents(
            status=status,
            severity=severity,
            service=service,
            limit=limit,
            offset=offset,
        )

    def get_incident(self, incident_id: str) -> IncidentRead | None:
        return self.repo.get_by_id(incident_id)

    def update_status(
        self,
        incident_id: str,
        status: IncidentStatus,
    ) -> IncidentRead | None:
        result = self.repo.update_status(incident_id, status)
        if result is not None:
            self.repo.conn.commit()
        return result
