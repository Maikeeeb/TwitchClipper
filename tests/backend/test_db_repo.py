"""
Test Plan
- Partitions: schema init, create/get job round trip, status updates, outputs save/list, result-like output persistence
- Boundaries: init called twice, empty outputs list, missing job lookup, rapid status rewrites, restart readback
- Failure modes: invalid db path, empty job_id, invalid status values, missing job update, non-string path values

Covers: TODO-DB-001, TODO-DB-002, TODO-DB-003
"""

from __future__ import annotations

import sqlite3

import pytest

from backend.db.models import OutputRecord
from backend.db.repo import SQLiteJobRepository
from backend.jobs import Job, JobStatus


def test_initialize_schema_is_idempotent(tmp_path) -> None:
    """Calling initialize_schema twice should keep tables valid."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    repo.initialize_schema()
    repo.initialize_schema()

    tables = repo.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('jobs', 'outputs')"
    ).fetchall()
    assert {row["name"] for row in tables} == {"jobs", "outputs"}
    repo.close()


def test_invalid_db_path_raises_sqlite_error(tmp_path) -> None:
    """A db path inside a missing directory should fail cleanly."""
    bad_path = tmp_path / "missing_dir" / "jobs.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        SQLiteJobRepository(str(bad_path))


def test_create_and_get_job_round_trip(tmp_path) -> None:
    """Create job in DB and load it back as a Job object."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    job = Job(type="vod_highlights", params={"vod_url": "https://www.twitch.tv/videos/123"})

    repo.create_job(job)
    loaded = repo.get_job(job.id)

    assert loaded is not None
    assert loaded.id == job.id
    assert loaded.type == "vod_highlights"
    assert loaded.status == JobStatus.QUEUED
    assert loaded.params["vod_url"] == "https://www.twitch.tv/videos/123"
    repo.close()


def test_get_job_missing_returns_none(tmp_path) -> None:
    """Missing row lookup should return None instead of raising."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    assert repo.get_job("missing-job") is None
    repo.close()


def test_update_job_status_validates_inputs(tmp_path) -> None:
    """Reject empty job_id and invalid status values."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    job = Job(type="clip_montage")
    repo.create_job(job)

    with pytest.raises(ValueError):
        repo.update_job_status("", "running")
    with pytest.raises(ValueError):
        repo.update_job_status(job.id, "not-a-status")
    repo.close()


def test_update_job_status_missing_job_returns_false(tmp_path) -> None:
    """Updating a non-existent job id should return False (clear not-found signal)."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    assert repo.update_job_status("does-not-exist", "running") is False
    repo.close()


def test_update_job_status_last_write_wins(tmp_path) -> None:
    """Two quick status updates should keep the latest state/value."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    job = Job(type="clip_montage")
    repo.create_job(job)

    assert repo.update_job_status(job.id, "running")
    assert repo.update_job_status(job.id, "failed", error="boom")

    loaded = repo.get_job(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.FAILED
    assert loaded.error == "boom"
    repo.close()


def test_update_job_status_truncates_error_message(tmp_path) -> None:
    """Failure reason should be stored safely with truncation for very long strings."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    job = Job(type="clip_montage")
    repo.create_job(job)

    long_error = "x" * 3000
    assert repo.update_job_status(job.id, "failed", error=long_error)
    loaded = repo.get_job(job.id)
    assert loaded is not None
    assert loaded.error is not None
    assert len(loaded.error) == 2048
    repo.close()


def test_save_outputs_handles_empty_and_round_trip(tmp_path) -> None:
    """Saving empty outputs is a no-op; valid outputs are retrievable."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    job = Job(type="clip_montage")
    repo.create_job(job)

    assert repo.save_outputs(job.id, []) == 0

    inserted = repo.save_outputs(
        job.id,
        [
            OutputRecord(job_id=job.id, kind="montage_path", path="/tmp/montage.mp4"),
            OutputRecord(job_id=job.id, kind="clips_dir", path="/tmp/clips"),
        ],
    )
    assert inserted == 2

    outputs = repo.list_outputs(job.id)
    assert [o.kind for o in outputs] == ["montage_path", "clips_dir"]
    assert [o.path for o in outputs] == ["/tmp/montage.mp4", "/tmp/clips"]
    repo.close()


def test_save_job_outputs_and_get_job_outputs_round_trip(tmp_path) -> None:
    """Persist final output paths from result-like dict and reconstruct them."""
    db_path = tmp_path / "jobs.sqlite3"
    repo = SQLiteJobRepository(str(db_path))
    job = Job(type="vod_highlights")
    repo.create_job(job)

    ok = repo.save_job_outputs(
        job.id,
        {
            "montage_path": "D:/out/final montage.mp4",
            "clips_dir": "D:/out/clips folder",
            "metadata_path": "D:/out/vod.json",
            "vod_path": "D:/out/vod.mp4",
            "chat_path": "D:/out/chat.jsonl",
            "paths": ["D:/out/clips folder/clip 1.mp4", "D:/out/clips folder/clip 2.mp4"],
        },
    )
    assert ok is True

    loaded = repo.get_job_outputs(job.id)
    assert loaded is not None
    assert loaded["montage_path"] == "D:/out/final montage.mp4"
    assert loaded["clips_dir"] == "D:/out/clips folder"
    assert loaded["metadata_path"] == "D:/out/vod.json"
    assert loaded["vod_path"] == "D:/out/vod.mp4"
    assert loaded["chat_path"] == "D:/out/chat.jsonl"
    assert loaded["paths"] == ["D:/out/clips folder/clip 1.mp4", "D:/out/clips folder/clip 2.mp4"]
    repo.close()


def test_save_job_outputs_missing_job_returns_false(tmp_path) -> None:
    """Saving outputs for unknown job should return False cleanly."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    assert repo.save_job_outputs("missing-job", {"montage_path": "/tmp/montage.mp4"}) is False
    repo.close()


def test_save_job_outputs_rejects_non_string_paths(tmp_path) -> None:
    """Non-string path values in output payload should be rejected."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    job = Job(type="clip_montage")
    repo.create_job(job)

    with pytest.raises(ValueError):
        repo.save_job_outputs(job.id, {"montage_path": 123})
    with pytest.raises(ValueError):
        repo.save_job_outputs(job.id, {"paths": ["ok", 5]})
    repo.close()


def test_get_job_outputs_restart_simulation(tmp_path) -> None:
    """Outputs should be retrievable by a new repository instance after reopen."""
    db_path = tmp_path / "jobs.sqlite3"
    repo = SQLiteJobRepository(str(db_path))
    job = Job(type="clip_montage")
    repo.create_job(job)
    repo.save_job_outputs(job.id, {"montage_path": "/tmp/m.mp4", "clips_dir": "/tmp/clips"})
    repo.close()

    repo_reopened = SQLiteJobRepository(str(db_path))
    loaded = repo_reopened.get_job_outputs(job.id)
    assert loaded == {"montage_path": "/tmp/m.mp4", "clips_dir": "/tmp/clips"}
    repo_reopened.close()
