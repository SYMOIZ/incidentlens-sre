# IncidentLens

Lightweight incident detection and log analysis — a production-shaped Python sample for SRE-style workflows.

**Greenfield note:** This checkout (`AWS weekly/python`) was empty when the project was created. IncidentLens is the only application here; there is no AWS lab content in this tree.

## What it does

- Ingest structured JSON logs via **REST API** or **CLI**
- Detect repeated errors, elevated error rates vs a simple baseline, and severity thresholds
- Fingerprint and **dedupe** ongoing issues into open/acknowledged incidents
- Persist incidents in **SQLite**
- List, filter, acknowledge, and resolve incidents

## Stack

Python 3.12+, FastAPI, Pydantic, SQLite, pytest, Ruff, Docker, stdlib logging.

## Quick start

```bash
python -m pip install -e ".[dev]"
make test          # or: python -m pytest -q
make lint          # or: python -m ruff check app tests
make run           # API on http://127.0.0.1:8000
```

API docs: http://127.0.0.1:8000/docs

### CLI

```bash
# Ingest sample JSONL (exit 1 if incidents created/updated; 0 if none; 2 on I/O/parse error)
python -m app.cli ingest examples/sample_logs.jsonl

# List open incidents
python -m app.cli list --status open
```

Or after install: `incidentlens ingest examples/sample_logs.jsonl`

### Docker

```bash
docker compose up --build
curl http://127.0.0.1:8000/health
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness |
| `POST` | `/logs` | Ingest one log object or `{"logs":[...]}` |
| `GET` | `/incidents` | List/filter (`status`, `severity`, `service`, `limit`, `offset`) |
| `GET` | `/incidents/{id}` | Fetch one |
| `PATCH` | `/incidents/{id}` | Update status (`open` / `acknowledged` / `resolved`) |

Example ingest:

```bash
curl -s -X POST http://127.0.0.1:8000/logs \
  -H "content-type: application/json" \
  -d '{"level":"ERROR","service":"checkout","message":"payment timeout id=1"}'
```

## Configuration

Copy `.env.example` to `.env`. All settings use the `INCIDENTLENS_` prefix (see `app/core/config.py`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `DB_PATH` | `incidentlens.db` | SQLite file |
| `ERROR_REPEAT_THRESHOLD` | `3` | Errors with same fingerprint in window → incident |
| `ERROR_WINDOW_SECONDS` | `300` | Sliding window for repeats / rate |
| `BASELINE_MULTIPLIER` | `3.0` | Recent count vs historical avg |
| `BASELINE_MIN_SAMPLES` | `20` | Cold-start guard for rate detection |

## Architecture

```
CLI / HTTP  →  IncidentService  →  DetectionEngine (pure)
                      ↓
              IncidentRepository  →  SQLite
```

- **Detection** has no I/O — unit-testable thresholds and fingerprinting
- **Service** owns ingest → detect → create/bump incident
- **API/CLI** stay thin adapters

## Project layout

```
app/
  api/          FastAPI routes + deps
  core/         settings, logging
  detection/    fingerprints + detection engine
  models/       Pydantic schemas
  storage/      SQLite schema + repository
  services.py   business orchestration
  cli.py        JSONL ingest + list
  main.py       app factory
tests/
examples/
```

## Reliability & security practices (sample scope)

- Input validation via Pydantic (size limits on message/batch)
- Validation errors return structured field errors, not raw request bodies
- SQLite parameterized queries; WAL mode
- Non-root Docker user; DB on a volume
- Stdlib structured logging for create/update paths
- No secrets in repo; config via env

## Limitations (honest)

- Single-process SQLite — not a multi-writer cluster store
- Baseline is a simple per-fingerprint window average, not seasonal/ML
- No authn/authz on the API (local/demo sample)
- Not deployed anywhere; no production traffic claims

## License

MIT
