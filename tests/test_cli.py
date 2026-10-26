from __future__ import annotations

from pathlib import Path

from app.cli import EXIT_ERROR, EXIT_INCIDENTS, EXIT_OK, main
from app.core.config import get_settings


def test_cli_ingest_creates_incidents(tmp_path, monkeypatch):
    db_path = tmp_path / "cli.db"
    monkeypatch.setenv("INCIDENTLENS_DB_PATH", str(db_path))
    get_settings.cache_clear()

    sample = Path(__file__).resolve().parents[1] / "examples" / "sample_logs.jsonl"
    code = main(["ingest", str(sample)])
    assert code == EXIT_INCIDENTS

    list_code = main(["list", "--status", "open"])
    assert list_code == EXIT_OK
    get_settings.cache_clear()


def test_cli_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("INCIDENTLENS_DB_PATH", str(tmp_path / "x.db"))
    get_settings.cache_clear()
    code = main(["ingest", str(tmp_path / "missing.jsonl")])
    assert code == EXIT_ERROR
    get_settings.cache_clear()


def test_cli_bad_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("INCIDENTLENS_DB_PATH", str(tmp_path / "x.db"))
    get_settings.cache_clear()
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not-json\n", encoding="utf-8")
    code = main(["ingest", str(bad)])
    assert code == EXIT_ERROR
    get_settings.cache_clear()
