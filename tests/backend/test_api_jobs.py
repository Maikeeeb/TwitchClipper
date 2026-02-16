"""
Test Plan
- Partitions: submit success, get found/not found, run_next empty vs one job
- Boundaries: empty streamer_names rejected by validation; unknown job_id → 404
- Failure modes: run_next with fake handler → DONE; no handler → FAILED (not exercised here)

Covers: TODO-JOBS-004
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is first on path so api.app resolves (pytest may prepend test dir)
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.app import create_app, get_now


def _fixed_now() -> datetime:
    return datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def app_with_fake_handler():
    """App with fake clip_montage handler so tests never call real pipeline."""
    app = create_app(handlers={"clip_montage": lambda job: {"ok": True}})
    app.dependency_overrides[get_now] = _fixed_now
    return app


@pytest.fixture
def client(app_with_fake_handler):
    return TestClient(app_with_fake_handler)


def test_submit_returns_job_id_and_job_is_queued(client: TestClient) -> None:
    """Validation: POST /jobs/clip-montage returns job_id and job is in queue."""
    resp = client.post(
        "/jobs/clip-montage",
        json={"streamer_names": ["streamer1"], "current_videos_dir": "."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    job_id = data["job_id"]
    assert isinstance(job_id, str)
    assert len(job_id) > 0

    # Job is queued: GET returns status queued
    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    job_data = get_resp.json()
    assert job_data["id"] == job_id
    assert job_data["type"] == "clip_montage"
    assert job_data["status"] == "queued"
    assert job_data["params"]["streamer_names"] == ["streamer1"]


def test_get_job_status_returns_fields(client: TestClient) -> None:
    """Validation: GET /jobs/{job_id} returns all JobResponse fields."""
    resp = client.post(
        "/jobs/clip-montage",
        json={"streamer_names": ["a"]},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == job_id
    assert data["type"] == "clip_montage"
    assert data["status"] in ("queued", "running", "done", "failed")
    assert "progress" in data
    assert "created_at" in data
    assert "started_at" in data
    assert "finished_at" in data
    assert "error" in data
    assert "result" in data
    assert "params" in data


def test_get_job_unknown_404(client: TestClient) -> None:
    """Defect: GET /jobs/{job_id} for unknown id returns 404."""
    resp = client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert "not found" in resp.json().get("detail", "").lower()


def test_run_next_moves_job_to_done_with_fake_handler(client: TestClient) -> None:
    """Validation: POST /jobs/run-next processes one job; fake handler sets status DONE."""
    resp = client.post(
        "/jobs/clip-montage",
        json={"streamer_names": ["x"]},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    run_resp = client.post("/jobs/run-next")
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["processed"] == 1
    assert data["job_id"] == job_id
    assert data["status"] == "done"

    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    job_data = get_resp.json()
    assert job_data["status"] == "done"
    assert job_data["result"] == {"ok": True}
    assert job_data["progress"] == pytest.approx(1.0)
    assert job_data["finished_at"] is not None


def test_run_next_empty_returns_processed_zero(client: TestClient) -> None:
    """Boundary: POST /jobs/run-next with empty queue returns processed: 0."""
    resp = client.post("/jobs/run-next")
    assert resp.status_code == 200
    assert resp.json() == {"processed": 0}


def test_submit_rejects_empty_streamer_names(client: TestClient) -> None:
    """Defect: POST /jobs/clip-montage with empty streamer_names is rejected."""
    resp = client.post(
        "/jobs/clip-montage",
        json={"streamer_names": []},
    )
    assert resp.status_code == 422


def test_health_returns_ok(client: TestClient) -> None:
    """Validation: GET /health returns ok true."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
