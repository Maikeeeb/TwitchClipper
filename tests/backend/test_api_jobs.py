"""
Test Plan
- Partitions: submit success for clip/vod jobs, get found/not found, run_next empty vs one job
- Boundaries: empty streamer_names rejected; missing vod_url rejected; unknown job_id -> 404
- Failure modes: run_next with fake handler -> DONE; no handler -> FAILED (not exercised here)

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


def test_list_jobs_returns_submitted_jobs(client: TestClient) -> None:
    """Validation: GET /jobs lists queued jobs for queue/dashboard views."""
    first = client.post("/jobs/clip-montage", json={"streamer_names": ["alpha"]})
    second = client.post("/jobs/vod-highlights", json={"vod_url": "https://www.twitch.tv/videos/123"})
    assert first.status_code == 200
    assert second.status_code == 200

    resp = client.get("/jobs")
    assert resp.status_code == 200
    payload = resp.json()
    ids = {item["id"] for item in payload}
    assert first.json()["job_id"] in ids
    assert second.json()["job_id"] in ids


def test_list_jobs_supports_status_filter(client: TestClient) -> None:
    """Boundary: GET /jobs with status filter only returns matching status entries."""
    queued = client.post("/jobs/clip-montage", json={"streamer_names": ["queued-job"]})
    assert queued.status_code == 200
    client.post("/jobs/run-next")

    resp = client.get("/jobs?status=done")
    assert resp.status_code == 200
    assert all(item["status"] == "done" for item in resp.json())


def test_list_jobs_rejects_invalid_status_filter(client: TestClient) -> None:
    """Defect: invalid status filter values are rejected with 422."""
    resp = client.get("/jobs?status=unknown")
    assert resp.status_code == 422


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


@pytest.mark.parametrize("streamer_names", [[""], ["   "], ["ok", "   "]])
def test_submit_rejects_blank_streamer_name_values(
    client: TestClient, streamer_names: list[str]
) -> None:
    """Defect: whitespace-only names are rejected even when list is non-empty."""
    resp = client.post(
        "/jobs/clip-montage",
        json={"streamer_names": streamer_names},
    )
    assert resp.status_code == 422


def test_submit_strips_surrounding_whitespace_in_streamer_names(client: TestClient) -> None:
    """Validation: accepted streamer names are normalized to trimmed values."""
    resp = client.post(
        "/jobs/clip-montage",
        json={"streamer_names": ["  streamer1  "]},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    payload = client.get(f"/jobs/{job_id}").json()
    assert payload["params"]["streamer_names"] == ["streamer1"]


def test_submit_vod_highlights_returns_job_id_and_queues_job() -> None:
    """Validation: POST /jobs/vod-highlights enqueues a vod_highlights job."""
    app = create_app(handlers={"vod_highlights": lambda job: {"ok": True}})
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)
    resp = client.post(
        "/jobs/vod-highlights",
        json={
            "vod_url": "https://www.twitch.tv/videos/123",
            "output_dir": ".",
            "keywords": ["wow"],
        },
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    queued = client.get(f"/jobs/{job_id}")
    assert queued.status_code == 200
    payload = queued.json()
    assert payload["type"] == "vod_highlights"
    assert payload["status"] == "queued"
    assert payload["params"]["vod_url"] == "https://www.twitch.tv/videos/123"
    assert payload["params"]["keywords"] == ["wow"]


def test_submit_vod_highlights_rejects_missing_vod_url() -> None:
    """Defect: POST /jobs/vod-highlights requires vod_url."""
    app = create_app(handlers={"vod_highlights": lambda job: {"ok": True}})
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)
    resp = client.post("/jobs/vod-highlights", json={"output_dir": "."})
    assert resp.status_code == 422


def test_run_next_processes_vod_highlights_job_with_fake_handler() -> None:
    """Validation: queued vod_highlights job transitions to done via /jobs/run-next."""
    app = create_app(handlers={"vod_highlights": lambda job: {"montage_path": "/tmp/m.mp4"}})
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)
    submit = client.post(
        "/jobs/vod-highlights",
        json={"vod_url": "https://www.twitch.tv/videos/123"},
    )
    assert submit.status_code == 200
    job_id = submit.json()["job_id"]

    run_resp = client.post("/jobs/run-next")
    assert run_resp.status_code == 200
    assert run_resp.json()["processed"] == 1
    assert run_resp.json()["status"] == "done"

    done = client.get(f"/jobs/{job_id}")
    assert done.status_code == 200
    assert done.json()["status"] == "done"
    assert done.json()["result"]["montage_path"] == "/tmp/m.mp4"


def test_health_returns_ok(client: TestClient) -> None:
    """Validation: GET /health returns ok true."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_health_rejects_non_get_methods(client: TestClient, method: str) -> None:
    """Defect: non-GET methods on /health return 405 method not allowed."""
    resp = client.request(method, "/health")
    assert resp.status_code == 405
