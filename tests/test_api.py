from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _error(service: str, message: str, seconds: int = 0) -> dict:
    ts = datetime.now(UTC) - timedelta(seconds=seconds)
    return {
        "timestamp": ts.isoformat().replace("+00:00", "Z"),
        "level": "ERROR",
        "service": service,
        "message": message,
    }


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ingest_creates_incident_after_repeats(client):
    for i in range(3):
        resp = client.post(
            "/logs",
            json=_error("checkout", f"payment timeout id={i:08x}"),
        )
        assert resp.status_code == 202

    body = resp.json()
    assert body["accepted"] == 1
    assert body["incidents_created"] + body["incidents_updated"] >= 1

    listed = client.get("/incidents")
    assert listed.status_code == 200
    incidents = listed.json()
    assert len(incidents) >= 1
    assert incidents[0]["service"] == "checkout"


def test_ingest_batch(client):
    payload = {
        "logs": [
            _error("payments", "card declined", 2),
            _error("payments", "card declined", 1),
            _error("payments", "card declined", 0),
        ]
    }
    resp = client.post("/logs", json=payload)
    assert resp.status_code == 202
    assert resp.json()["accepted"] == 3


def test_get_and_patch_incident(client):
    for i in range(3):
        client.post("/logs", json=_error("auth", f"store down {i}"))

    incidents = client.get("/incidents").json()
    assert incidents
    iid = incidents[0]["id"]

    got = client.get(f"/incidents/{iid}")
    assert got.status_code == 200
    assert got.json()["id"] == iid

    patched = client.patch(f"/incidents/{iid}", json={"status": "acknowledged"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "acknowledged"

    resolved = client.patch(f"/incidents/{iid}", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_filter_by_status(client):
    for i in range(3):
        client.post("/logs", json=_error("svc", f"fail {i}"))
    incidents = client.get("/incidents").json()
    iid = incidents[0]["id"]
    client.patch(f"/incidents/{iid}", json={"status": "resolved"})

    open_only = client.get("/incidents", params={"status": "open"}).json()
    assert all(i["status"] == "open" for i in open_only)
    assert iid not in {i["id"] for i in open_only}


def test_unknown_incident_404(client):
    assert client.get("/incidents/does-not-exist").status_code == 404


def test_validation_error(client):
    resp = client.post("/logs", json={"level": "ERROR"})
    assert resp.status_code == 422


def test_dedupe_updates_open_incident(client):
    for i in range(3):
        client.post("/logs", json=_error("checkout", f"payment timeout id={i:08x}"))
    first = client.get("/incidents", params={"service": "checkout"}).json()
    assert len(first) == 1
    iid = first[0]["id"]
    prior_count = first[0]["count"]

    client.post("/logs", json=_error("checkout", "payment timeout id=zzzzzzzz"))
    second = client.get("/incidents", params={"service": "checkout"}).json()
    assert len(second) == 1
    assert second[0]["id"] == iid
    assert second[0]["count"] >= prior_count
