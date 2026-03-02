"""
How to run:
pytest tests/backend/test_db_sqlite.py -v

Test Plan
- Partitions: schema init, job create/read, status transitions, output save/read, multi-job isolation
- Boundaries: schema init called twice, missing rows, optional output fields omitted
- Failure modes: invalid DB path, invalid status, invalid/missing job_id, non-string output paths

Covers: TODO-DB-004
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from backend.db.repo import SQLiteJobRepository
from backend.models.jobs import Job, JobStatus


def _fixed_dt(hour: int) -> datetime:
    return datetime(2025, 2, 15, hour, 0, 0, tzinfo=timezone.utc)


def test_schema_init_is_idempotent(tmp_path) -> None:
    """Schema creation should be safe to call more than once."""
    db_path = tmp_path / "jobs.sqlite3"
    repo = SQLiteJobRepository(str(db_path))

    repo.initialize_schema()
    repo.initialize_schema()

    rows = repo.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC"
    ).fetchall()
    names = {row["name"] for row in rows}
    assert "jobs" in names
    assert "outputs" in names
    repo.close()


def test_invalid_db_path_raises_operational_error(tmp_path) -> None:
    """Path under a missing directory should fail with sqlite operational error."""
    bad_path = tmp_path / "missing-parent" / "jobs.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        SQLiteJobRepository(str(bad_path))


def test_job_create_and_read_round_trip() -> None:
    """A persisted job should load back with matching fields."""
    repo = SQLiteJobRepository(":memory:")
    job = Job(
        id="job-fixed-001",
        type="vod_highlights",
        created_at=_fixed_dt(10),
        params={"vod_url": "https://www.twitch.tv/videos/123"},
    )
    repo.create_job(job)

    loaded = repo.get_job("job-fixed-001")
    assert loaded is not None
    assert loaded.id == "job-fixed-001"
    assert loaded.type == "vod_highlights"
    assert loaded.status == JobStatus.QUEUED
    assert loaded.params == {"vod_url": "https://www.twitch.tv/videos/123"}
    repo.close()


def test_job_status_lifecycle_transitions_and_timestamps() -> None:
    """Status updates should persist queued -> running -> done with expected fields."""
    repo = SQLiteJobRepository(":memory:")
    job = Job(id="job-fixed-002", type="clip_montage", created_at=_fixed_dt(9))
    repo.create_job(job)

    assert repo.update_job_status(
        "job-fixed-002",
        "running",
        progress=0.2,
        started_at=_fixed_dt(10),
    )
    running = repo.get_job("job-fixed-002")
    assert running is not None
    assert running.status == JobStatus.RUNNING
    assert running.progress == pytest.approx(0.2)
    assert running.started_at == _fixed_dt(10)
    assert running.finished_at is None

    assert repo.update_job_status(
        "job-fixed-002",
        "done",
        progress=1.0,
        finished_at=_fixed_dt(11),
        result={"montage_path": "/tmp/montage.mp4"},
    )
    done = repo.get_job("job-fixed-002")
    assert done is not None
    assert done.status == JobStatus.DONE
    assert done.progress == pytest.approx(1.0)
    assert done.finished_at == _fixed_dt(11)
    assert done.result == {"montage_path": "/tmp/montage.mp4"}
    repo.close()


def test_missing_job_read_and_update_behaviors() -> None:
    """Missing job reads should return None; missing updates should return False."""
    repo = SQLiteJobRepository(":memory:")
    assert repo.get_job("nope") is None
    assert repo.update_job_status("nope", "running") is False
    assert repo.get_job_outputs("nope") is None
    assert repo.save_job_outputs("nope", {"montage_path": "/tmp/m.mp4"}) is False
    repo.close()


def test_outputs_save_and_read_with_optional_fields_missing() -> None:
    """Saving subset of output fields should persist only provided path keys."""
    repo = SQLiteJobRepository(":memory:")
    job = Job(id="job-fixed-003", type="vod_highlights")
    repo.create_job(job)

    assert repo.save_job_outputs(
        "job-fixed-003",
        {
            "montage_path": "/tmp/final.mp4",
            "clips_dir": "/tmp/clips",
            "chat_path": None,  # optional and absent in storage
            "metadata_path": "/tmp/meta.json",
        },
    )
    outputs = repo.get_job_outputs("job-fixed-003")
    assert outputs is not None
    assert outputs == {
        "clips_dir": "/tmp/clips",
        "metadata_path": "/tmp/meta.json",
        "montage_path": "/tmp/final.mp4",
    }
    repo.close()


def test_outputs_reject_non_string_paths() -> None:
    """Non-string output paths should raise clear ValueError."""
    repo = SQLiteJobRepository(":memory:")
    job = Job(id="job-fixed-004", type="clip_montage")
    repo.create_job(job)

    with pytest.raises(ValueError):
        repo.save_job_outputs("job-fixed-004", {"montage_path": 123})
    with pytest.raises(ValueError):
        repo.save_job_outputs("job-fixed-004", {"paths": ["ok", 999]})
    repo.close()


def test_invalid_status_and_missing_job_id_are_rejected() -> None:
    """Public repo methods should reject invalid status and empty job_id values."""
    repo = SQLiteJobRepository(":memory:")
    job = Job(id="job-fixed-005", type="clip_montage")
    repo.create_job(job)

    with pytest.raises(ValueError):
        repo.update_job_status("job-fixed-005", "bad-status")
    with pytest.raises(ValueError):
        repo.update_job_status("", "running")
    with pytest.raises(ValueError):
        repo.get_job("")
    with pytest.raises(ValueError):
        repo.save_job_outputs("", {"montage_path": "/tmp/m.mp4"})
    repo.close()


def test_long_error_is_truncated_safely() -> None:
    """Very long failure strings should be truncated to safe storage length."""
    repo = SQLiteJobRepository(":memory:")
    job = Job(id="job-fixed-006", type="clip_montage")
    repo.create_job(job)

    long_error = "E" * 3000
    assert repo.update_job_status("job-fixed-006", "failed", error=long_error)
    loaded = repo.get_job("job-fixed-006")
    assert loaded is not None
    assert loaded.status == JobStatus.FAILED
    assert loaded.error is not None
    assert len(loaded.error) == 2048
    repo.close()


def test_multiple_jobs_are_isolated() -> None:
    """Multiple persisted jobs should keep independent status and outputs."""
    repo = SQLiteJobRepository(":memory:")
    j1 = Job(id="job-fixed-007", type="clip_montage")
    j2 = Job(id="job-fixed-008", type="vod_highlights")
    repo.create_job(j1)
    repo.create_job(j2)

    assert repo.update_job_status("job-fixed-007", "done", result={"montage_path": "/tmp/a.mp4"})
    assert repo.update_job_status("job-fixed-008", "failed", error="boom")
    assert repo.save_job_outputs("job-fixed-007", {"montage_path": "/tmp/a.mp4", "clips_dir": "/tmp/a"})

    j1_loaded = repo.get_job("job-fixed-007")
    j2_loaded = repo.get_job("job-fixed-008")
    assert j1_loaded is not None and j1_loaded.status == JobStatus.DONE
    assert j2_loaded is not None and j2_loaded.status == JobStatus.FAILED

    out1 = repo.get_job_outputs("job-fixed-007")
    out2 = repo.get_job_outputs("job-fixed-008")
    assert out1 == {"clips_dir": "/tmp/a", "montage_path": "/tmp/a.mp4"}
    assert out2 == {}
    repo.close()
