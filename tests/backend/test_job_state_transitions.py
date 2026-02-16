"""
Test Plan
- Partitions: DONE path (success), FAILED path (handler exception, no handler)
- Boundaries: FIFO order, run_next processes exactly one job per call
- Failure modes: handler raises → FAILED; no handler registered → FAILED

End-to-end job state transitions via API + worker. Deterministic via get_now override.

Covers: TODO-JOBS-005
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.app import create_app, get_now

FIXED_NOW = datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _fixed_now() -> datetime:
    return FIXED_NOW


def _submit(client: TestClient, streamer: str = "x") -> str:
    """Submit a clip-montage job and return job_id."""
    resp = client.post(
        "/jobs/clip-montage",
        json={"streamer_names": [streamer]},
    )
    assert resp.status_code == 200
    return resp.json()["job_id"]


def test_job_transitions_queued_running_done_via_run_next() -> None:
    """DONE path: queued -> run_next -> running -> done; timestamps and result set."""
    app = create_app(handlers={"clip_montage": lambda job: {"ok": True}})
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    job_id = _submit(client)
    # Before run-next: QUEUED
    r = client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "queued"
    assert j["started_at"] is None
    assert j["finished_at"] is None
    assert j["progress"] == 0.0

    # run-next
    rn = client.post("/jobs/run-next")
    assert rn.status_code == 200
    assert rn.json()["processed"] == 1
    assert rn.json()["job_id"] == job_id
    assert rn.json()["status"] == "done"

    # After run-next: DONE
    r = client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "done"
    assert j["started_at"] is not None
    assert j["finished_at"] is not None
    assert j["progress"] == 1.0
    assert j["result"] == {"ok": True}
    assert j["error"] is None


def test_job_transitions_queued_running_failed_on_exception() -> None:
    """FAILED path: handler raises ValueError -> job marked FAILED, error set, result None."""

    def boom(_job):
        raise ValueError("boom")

    app = create_app(handlers={"clip_montage": boom})
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    job_id = _submit(client)
    rn = client.post("/jobs/run-next")
    assert rn.status_code == 200
    assert rn.json()["processed"] == 1
    assert rn.json()["status"] == "failed"

    r = client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "failed"
    assert j["started_at"] is not None
    assert j["finished_at"] is not None
    assert "boom" in (j["error"] or "")
    assert j["result"] is None


def test_job_fails_when_no_handler_registered() -> None:
    """FAILED path: no handler for clip_montage -> FAILED with clear error message."""
    # Handlers dict without clip_montage (handlers={} would fall back to default_handlers())
    app = create_app(handlers={"other_type": lambda job: {}})
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    job_id = _submit(client)
    rn = client.post("/jobs/run-next")
    assert rn.status_code == 200
    assert rn.json()["processed"] == 1
    assert rn.json()["status"] == "failed"

    r = client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "failed"
    assert "No handler registered for job type" in (j["error"] or "")


def test_run_next_processes_one_job_only_fifo() -> None:
    """run-next processes exactly one job per call; order is FIFO."""
    app = create_app(handlers={"clip_montage": lambda job: {"ok": True}})
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    job_a = _submit(client, "a")
    job_b = _submit(client, "b")

    rn = client.post("/jobs/run-next")
    assert rn.status_code == 200
    assert rn.json()["processed"] == 1
    assert rn.json()["job_id"] == job_a

    r = client.get(f"/jobs/{job_a}")
    assert r.json()["status"] == "done"
    r = client.get(f"/jobs/{job_b}")
    assert r.json()["status"] == "queued"

    rn = client.post("/jobs/run-next")
    assert rn.status_code == 200
    assert rn.json()["processed"] == 1
    assert rn.json()["job_id"] == job_b

    r = client.get(f"/jobs/{job_b}")
    assert r.json()["status"] == "done"


def test_job_datetime_fields_are_iso_utc() -> None:
    """Datetime fields are ISO strings and timezone-aware (UTC)."""
    app = create_app(handlers={"clip_montage": lambda job: {"ok": True}})
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    job_id = _submit(client)
    client.post("/jobs/run-next")

    r = client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    j = r.json()
    for key in ("created_at", "started_at", "finished_at"):
        val = j.get(key)
        assert val is not None, f"{key} should be set"
        parsed = datetime.fromisoformat(val.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, f"{key} should be timezone-aware"
