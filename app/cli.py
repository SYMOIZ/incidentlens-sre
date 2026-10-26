"""CLI for JSONL log ingest and incident listing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.models.schemas import IncidentStatus, LogEntry, Severity
from app.services import IncidentService
from app.storage.database import Database
from app.storage.repository import IncidentRepository

EXIT_OK = 0
EXIT_INCIDENTS = 1
EXIT_ERROR = 2


def _load_jsonl(path: Path) -> list[LogEntry]:
    entries: list[LogEntry] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                entries.append(LogEntry.model_validate(payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
    if not entries:
        raise ValueError(f"{path}: no log entries found")
    return entries


def _print_ingest(result) -> None:
    print(
        f"Accepted {result.accepted} log(s): "
        f"{result.incidents_created} created, {result.incidents_updated} updated"
    )
    if result.incident_ids:
        print("Incident IDs:")
        for iid in result.incident_ids:
            print(f"  - {iid}")


def _print_incidents(incidents) -> None:
    if not incidents:
        print("No incidents matched.")
        return
    for inc in incidents:
        print(
            f"[{inc.severity.value:8}] {inc.status.value:12} "
            f"{inc.id}  {inc.service}  count={inc.count}"
        )
        print(f"  {inc.title}")


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    setup_logging(settings.log_level)
    path = Path(args.file)
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return EXIT_ERROR

    try:
        logs = _load_jsonl(path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    db = Database(settings.db_path)
    db.initialize()
    conn = db.connect()
    try:
        service = IncidentService(IncidentRepository(conn), settings)
        result = service.ingest(logs)
    finally:
        conn.close()

    _print_ingest(result)
    if result.incidents_created or result.incidents_updated:
        return EXIT_INCIDENTS
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    settings = get_settings()
    setup_logging(settings.log_level)
    db = Database(settings.db_path)
    db.initialize()
    conn = db.connect()
    try:
        service = IncidentService(IncidentRepository(conn), settings)
        status = IncidentStatus(args.status) if args.status else None
        severity = Severity(args.severity) if args.severity else None
        incidents = service.list_incidents(
            status=status,
            severity=severity,
            service=args.service,
            limit=args.limit,
        )
    finally:
        conn.close()
    _print_incidents(incidents)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="incidentlens",
        description="IncidentLens CLI — ingest JSONL logs and list incidents",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest a JSONL log file")
    ingest.add_argument("file", help="Path to JSONL file")
    ingest.set_defaults(func=cmd_ingest)

    listing = sub.add_parser("list", help="List incidents")
    listing.add_argument("--status", choices=[s.value for s in IncidentStatus])
    listing.add_argument("--severity", choices=[s.value for s in Severity])
    listing.add_argument("--service")
    listing.add_argument("--limit", type=int, default=50)
    listing.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
