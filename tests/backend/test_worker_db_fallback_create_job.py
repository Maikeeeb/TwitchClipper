"""
How to run:
pytest tests/backend/test_worker_db_fallback_create_job.py -v

Test Plan
- Partitions: missing DB row fallback path and normal update path on subsequent transition
- Edge cases: update_job_status returns False on first persist; second persist should not duplicate row
- Failure mode: missing DB row should self-heal via create_job without raising
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.db.repo import SQLiteJobRepository
from backend.job_queue import InMemoryJobQueue
from backend.jobs import JobStatus
from backend.worker import Worker


def _dt(hour: int) -> datetime:
    return datetime(2025, 2, 15, hour, 0, 0, tzinfo=timezone.utc)


def test_worker_creates_job_row_when_status_update_returns_false(tmp_path) -> None:
    """Worker should create missing DB row, then continue normal status persistence."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    queue = InMemoryJobQueue()
    job = queue.create_job("demo")
    queue.enqueue(job)

    # NOTE: do not call repo.create_job(job); force update_job_status -> False fallback path.
    worker = Worker(
        queue,
        handlers={"demo": lambda _job: {"montage_path": "/tmp/fallback.mp4"}},
        job_repo=repo,
    )

    out = worker.run_next(now=_dt(12))
    assert out is job

    loaded = repo.get_job(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.DONE
    assert loaded.started_at == _dt(12)
    assert loaded.finished_at == _dt(12)
    assert loaded.result == {"montage_path": "/tmp/fallback.mp4"}

    # Run a second transition to ensure persistence now updates same row, not duplicates.
    queue.enqueue(job)
    worker.handlers["demo"] = lambda _job: {"montage_path": "/tmp/second.mp4"}
    out2 = worker.run_next(now=_dt(13))
    assert out2 is job

    loaded_again = repo.get_job(job.id)
    assert loaded_again is not None
    assert loaded_again.status == JobStatus.DONE
    assert loaded_again.started_at == _dt(13)
    assert loaded_again.finished_at == _dt(13)
    assert loaded_again.result == {"montage_path": "/tmp/second.mp4"}

    # Explicit duplicate guard check: only one row should exist for the job id.
    count = repo.connection.execute(
        "SELECT COUNT(*) AS c FROM jobs WHERE id = ?",
        (job.id,),
    ).fetchone()["c"]
    assert count == 1
    repo.close()
