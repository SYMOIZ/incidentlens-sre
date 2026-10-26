from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import Settings
from app.models.schemas import LogEntry
from app.services import IncidentService
from app.storage.database import Database
from app.storage.repository import IncidentRepository


def test_info_logs_do_not_open_incidents(tmp_path):
    settings = Settings(db_path=str(tmp_path / "s.db"), error_repeat_threshold=3)
    db = Database(settings.db_path)
    db.initialize()
    conn = db.connect()
    service = IncidentService(IncidentRepository(conn), settings)

    result = service.ingest(
        [
            LogEntry(
                timestamp=datetime.now(UTC),
                level="INFO",
                service="web",
                message="ok",
            )
        ]
    )
    assert result.incidents_created == 0
    assert service.list_incidents() == []
    conn.close()
