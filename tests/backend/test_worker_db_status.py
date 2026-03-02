"""
Test Plan
- Partitions: worker status persistence for success/failure/crash-like interruption
- Boundaries: status transitions are written only at transition points
- Failure modes: handler exception -> FAILED; BaseException interruption keeps RUNNING

Covers: TODO-DB-002
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.db.repo import SQLiteJobRepository
from backend.job_queue import InMemoryJobQueue
from backend.models.jobs import JobStatus
from backend.worker import Worker


def _fixed_now() -> datetime:
    return datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_worker_persists_status_done_timeline(tmp_path) -> None:
    """Happy path run persists QUEUED -> RUNNING -> DONE in SQLite."""
    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    queue = InMemoryJobQueue()
    job = queue.create_job("demo")
    repo.create_job(job)
    queue.enqueue(job)
    worker = Worker(queue, handlers={"demo": lambda _j: {"ok": True}}, job_repo=repo)

    before = repo.get_job(job.id)
    assert before is not None
    assert before.status == JobStatus.QUEUED

    worker.run_next(now=_fixed_now())
    after = repo.get_job(job.id)
    assert after is not None
    assert after.status == JobStatus.DONE
    assert after.started_at is not None
    assert after.finished_at is not None
    repo.close()


def test_worker_persists_failed_status_and_error(tmp_path) -> None:
    """Handler exception should persist FAILED state with failure reason."""

    def _boom(_job):
        raise RuntimeError("handler exploded")

    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    queue = InMemoryJobQueue()
    job = queue.create_job("demo")
    repo.create_job(job)
    queue.enqueue(job)
    worker = Worker(queue, handlers={"demo": _boom}, job_repo=repo)

    worker.run_next(now=_fixed_now())
    loaded = repo.get_job(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.FAILED
    assert loaded.error is not None
    assert "handler exploded" in loaded.error
    repo.close()


def test_worker_interruption_leaves_running_status_in_db(tmp_path) -> None:
    """If handler aborts with BaseException, DB should remain RUNNING (not silently DONE)."""

    def _interrupt(_job):
        raise KeyboardInterrupt("simulated interrupt")

    repo = SQLiteJobRepository(str(tmp_path / "jobs.sqlite3"))
    queue = InMemoryJobQueue()
    job = queue.create_job("demo")
    repo.create_job(job)
    queue.enqueue(job)
    worker = Worker(queue, handlers={"demo": _interrupt}, job_repo=repo)

    with pytest.raises(KeyboardInterrupt):
        worker.run_next(now=_fixed_now())

    loaded = repo.get_job(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.RUNNING
    assert loaded.finished_at is None
    repo.close()
