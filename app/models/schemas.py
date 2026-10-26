"""Pydantic schemas for logs and incidents."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class LogEntry(BaseModel):
    """Single structured log line accepted by the ingest API/CLI."""

    timestamp: datetime | None = None
    level: str = Field(..., min_length=1, max_length=32)
    service: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=4096)
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("level")
    @classmethod
    def normalize_level(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("service")
    @classmethod
    def strip_service(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("service must not be blank")
        return cleaned


class LogBatch(BaseModel):
    logs: list[LogEntry] = Field(..., min_length=1, max_length=1000)


class IncidentCreate(BaseModel):
    fingerprint: str
    title: str
    severity: Severity
    service: str
    count: int = 1
    sample_message: str
    first_seen: datetime
    last_seen: datetime


class IncidentUpdate(BaseModel):
    status: IncidentStatus


class IncidentRead(BaseModel):
    id: str
    fingerprint: str
    title: str
    severity: Severity
    status: IncidentStatus
    service: str
    count: int
    sample_message: str
    first_seen: datetime
    last_seen: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IngestResult(BaseModel):
    accepted: int
    incidents_created: int
    incidents_updated: int
    incident_ids: list[str]
