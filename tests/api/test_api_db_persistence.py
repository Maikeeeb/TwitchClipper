"""
Test Plan
- Partitions: API submit persistence, worker status persistence, output persistence, DB read behavior
- Boundaries: DB enabled with temp file path, restart reads from persisted DB
- Failure modes: queue-memory divergence should still read persisted DB state

Covers: TODO-DB-001, TODO-DB-002, TODO-DB-003
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.app import create_app, get_now
from backend.db.repo import SQLiteJobRepository
from backend.models.jobs import JobStatus


def _fixed_now() -> datetime:
    return datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_submit_job_persists_row_when_db_enabled(tmp_path) -> None:
    """Submitting job should write an initial row to SQLite when enabled."""
    db_path = tmp_path / "jobs.sqlite3"
    app = create_app(
        handlers={"clip_montage": lambda _job: {"ok": True}},
        db_enabled=True,
        db_path=str(db_path),
    )
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    submit = client.post("/jobs/clip-montage", json={"streamer_names": ["a"], "current_videos_dir": "."})
    assert submit.status_code == 200
    job_id = submit.json()["job_id"]

    repo = SQLiteJobRepository(str(db_path))
    loaded = repo.get_job(job_id)
    assert loaded is not None
    assert loaded.status.value == "queued"
    repo.close()


def test_run_next_updates_status_and_outputs_in_db(tmp_path) -> None:
    """run-next should persist terminal status/result and output paths."""
    db_path = tmp_path / "jobs.sqlite3"
    app = create_app(
        handlers={
            "clip_montage": lambda _job: {
                "montage_path": "/tmp/montage.mp4",
                "paths": ["/tmp/clip1.mp4", "/tmp/clip2.mp4"],
            }
        },
        db_enabled=True,
        db_path=str(db_path),
    )
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    submit = client.post("/jobs/clip-montage", json={"streamer_names": ["a"], "current_videos_dir": "."})
    assert submit.status_code == 200
    job_id = submit.json()["job_id"]

    run_resp = client.post("/jobs/run-next")
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "done"

    repo = SQLiteJobRepository(str(db_path))
    loaded = repo.get_job(job_id)
    assert loaded is not None
    assert loaded.status.value == "done"
    assert loaded.result is not None
    assert loaded.result["montage_path"] == "/tmp/montage.mp4"
    stored_outputs = repo.get_job_outputs(job_id)
    assert stored_outputs is not None
    assert stored_outputs["montage_path"] == "/tmp/montage.mp4"

    outputs = repo.list_outputs(job_id)
    assert [out.kind for out in outputs] == ["montage_path", "path", "path"]
    repo.close()


def test_get_job_reads_from_db_when_enabled(tmp_path) -> None:
    """When DB is enabled, GET /jobs/{id} should use persisted DB state as source of truth."""
    db_path = tmp_path / "jobs.sqlite3"
    app = create_app(
        handlers={"clip_montage": lambda _job: {"ok": True}},
        db_enabled=True,
        db_path=str(db_path),
    )
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    submit = client.post("/jobs/clip-montage", json={"streamer_names": ["a"], "current_videos_dir": "."})
    assert submit.status_code == 200
    job_id = submit.json()["job_id"]

    # Mutate only in-memory job to a contradictory state.
    in_memory_job = app.state.queue.get(job_id)
    assert in_memory_job is not None
    in_memory_job.status = JobStatus.FAILED
    in_memory_job.error = "memory-only divergence"

    # Persisted DB row remains queued, and API must reflect DB row.
    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    payload = get_resp.json()
    assert payload["status"] == "queued"
    assert payload["error"] is None


def test_get_job_returns_persisted_outputs_after_restart(tmp_path) -> None:
    """API should return persisted outputs even with a fresh app/empty in-memory queue."""
    db_path = tmp_path / "jobs.sqlite3"

    app1 = create_app(
        handlers={
            "clip_montage": lambda _job: {
                "montage_path": "/tmp/montage.mp4",
                "clips_dir": "/tmp/clips",
                "metadata_path": "/tmp/meta.json",
                "vod_path": "/tmp/vod.mp4",
                "chat_path": "/tmp/chat.jsonl",
            }
        },
        db_enabled=True,
        db_path=str(db_path),
    )
    app1.dependency_overrides[get_now] = _fixed_now
    client1 = TestClient(app1)

    submit = client1.post("/jobs/clip-montage", json={"streamer_names": ["a"], "current_videos_dir": "."})
    assert submit.status_code == 200
    job_id = submit.json()["job_id"]
    run_resp = client1.post("/jobs/run-next")
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "done"

    # Simulate restart: new app with new queue instance, same DB.
    app2 = create_app(
        handlers={"clip_montage": lambda _job: {"ok": True}},
        db_enabled=True,
        db_path=str(db_path),
    )
    app2.dependency_overrides[get_now] = _fixed_now
    client2 = TestClient(app2)

    get_resp = client2.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    payload = get_resp.json()
    assert payload["status"] == "done"
    assert payload["outputs"]["montage_path"] == "/tmp/montage.mp4"
    assert payload["outputs"]["clips_dir"] == "/tmp/clips"
    assert payload["outputs"]["metadata_path"] == "/tmp/meta.json"
    assert payload["outputs"]["vod_path"] == "/tmp/vod.mp4"
    assert payload["outputs"]["chat_path"] == "/tmp/chat.jsonl"
