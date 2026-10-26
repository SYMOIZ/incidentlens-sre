"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.services import IncidentService
from app.storage.database import Database
from app.storage.repository import IncidentRepository


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[IncidentService, None, None]:
    db: Database = request.app.state.db
    conn = db.connect()
    try:
        yield IncidentService(IncidentRepository(conn), settings)
    finally:
        conn.close()
