"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def settings(tmp_path, monkeypatch) -> Settings:
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("INCIDENTLENS_DB_PATH", db_path)
    monkeypatch.setenv("INCIDENTLENS_ERROR_REPEAT_THRESHOLD", "3")
    monkeypatch.setenv("INCIDENTLENS_ERROR_WINDOW_SECONDS", "300")
    monkeypatch.setenv("INCIDENTLENS_BASELINE_MULTIPLIER", "3.0")
    monkeypatch.setenv("INCIDENTLENS_BASELINE_MIN_SAMPLES", "20")
    get_settings.cache_clear()
    return Settings(
        db_path=db_path,
        error_repeat_threshold=3,
        error_window_seconds=300,
        baseline_multiplier=3.0,
        baseline_min_samples=20,
    )


@pytest.fixture
def client(settings: Settings):
    get_settings.cache_clear()

    def _override() -> Settings:
        return settings

    app.dependency_overrides[get_settings] = _override

    with TestClient(app) as test_client:
        # Lifespan initialized DB from env; assert we are on the temp path.
        assert app.state.db.path == settings.db_path
        yield test_client

    app.dependency_overrides.clear()
    get_settings.cache_clear()
