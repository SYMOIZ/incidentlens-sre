"""REST routes for health, log ingest, and incident management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_service
from app.models.schemas import (
    IncidentRead,
    IncidentStatus,
    IncidentUpdate,
    IngestResult,
    LogBatch,
    LogEntry,
    Severity,
)
from app.services import IncidentService

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/logs", response_model=IngestResult, status_code=status.HTTP_202_ACCEPTED)
def ingest_logs(
    payload: LogEntry | LogBatch,
    service: Annotated[IncidentService, Depends(get_service)],
) -> IngestResult:
    if isinstance(payload, LogEntry):
        logs = [payload]
    else:
        logs = payload.logs
    return service.ingest(logs)


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    service: Annotated[IncidentService, Depends(get_service)],
    status_filter: Annotated[
        IncidentStatus | None,
        Query(alias="status"),
    ] = None,
    severity: Severity | None = None,
    service_name: Annotated[str | None, Query(alias="service")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IncidentRead]:
    return service.list_incidents(
        status=status_filter,
        severity=severity,
        service=service_name,
        limit=limit,
        offset=offset,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: str,
    service: Annotated[IncidentService, Depends(get_service)],
) -> IncidentRead:
    incident = service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
def patch_incident(
    incident_id: str,
    body: IncidentUpdate,
    service: Annotated[IncidentService, Depends(get_service)],
) -> IncidentRead:
    incident = service.update_status(incident_id, body.status)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
