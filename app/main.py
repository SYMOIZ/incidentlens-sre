"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.storage.database import Database


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    db = Database(settings.db_path)
    db.initialize()
    app.state.db = db
    yield


app = FastAPI(
    title="IncidentLens",
    description="Lightweight incident detection and log analysis",
    version=__version__,
    lifespan=lifespan,
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    # Avoid echoing raw body; return structured field errors only.
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )
