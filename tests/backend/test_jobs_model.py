"""
Test Plan
- Partitions: JobStatus values, Job defaults, start/succeed/fail transitions
- Boundaries: progress default 0.0, succeed sets 1.0; optional result/error
- Failure modes: none (methods are mutators; no invalid input in this ticket)

Covers: TODO-JOBS-001
"""

from datetime import datetime, timezone

import pytest

from backend.jobs import Job, JobStatus


def test_job_defaults_are_queued_and_has_uuid() -> None:
    """Validation: new Job has status QUEUED and a non-empty uuid4-style id."""
    job = Job(type="clip_montage")
    assert job.status == JobStatus.QUEUED
    assert job.id != ""
    assert len(job.id) == 36
    assert job.id.count("-") == 4
    assert job.started_at is None
    assert job.finished_at is None
    assert job.error is None
    assert job.result is None
    assert job.progress == pytest.approx(0.0)
    assert job.params == {}


def test_job_start_sets_running_and_started_at() -> None:
    """Validation: start(now) sets status RUNNING and started_at."""
    fixed = datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
    job = Job(type="clip_montage", id="j1", created_at=fixed)
    job.start(fixed)
    assert job.status == JobStatus.RUNNING
    assert job.started_at == fixed


def test_job_succeed_sets_done_finished_progress_and_result() -> None:
    """Validation: succeed(result, now) sets DONE, finished_at, progress=1.0, result; clears error."""
    fixed = datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
    job = Job(type="clip_montage", id="j1", created_at=fixed, error="old")
    job.start(fixed)
    job.succeed({"output": "/path/to/montage.mp4"}, fixed)
    assert job.status == JobStatus.DONE
    assert job.finished_at == fixed
    assert job.progress == pytest.approx(1.0)
    assert job.result == {"output": "/path/to/montage.mp4"}
    assert job.error is None


def test_job_fail_sets_failed_finished_and_error() -> None:
    """Validation: fail(error, now) sets FAILED, finished_at, error; result stays None."""
    fixed = datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
    job = Job(type="clip_montage", id="j1", created_at=fixed)
    job.start(fixed)
    job.fail("download timeout", fixed)
    assert job.status == JobStatus.FAILED
    assert job.finished_at == fixed
    assert job.error == "download timeout"
    assert job.result is None


def test_job_methods_do_not_crash_when_called_in_order() -> None:
    """Validation: queued -> running -> done and queued -> running -> failed both succeed."""
    fixed = datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
    job_done = Job(type="clip_montage", id="j1", created_at=fixed)
    job_done.start(fixed)
    job_done.succeed({"out": "x.mp4"}, fixed)
    assert job_done.status == JobStatus.DONE

    job_failed = Job(type="clip_montage", id="j2", created_at=fixed)
    job_failed.start(fixed)
    job_failed.fail("error", fixed)
    assert job_failed.status == JobStatus.FAILED


def test_progress_clamped_or_valid_range() -> None:
    """Boundary: default progress is 0.0; succeed sets progress to 1.0."""
    fixed = datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
    job = Job(type="clip_montage", id="j1", created_at=fixed)
    assert job.progress == pytest.approx(0.0)
    job.start(fixed)
    assert job.progress == pytest.approx(0.0)
    job.succeed({}, fixed)
    assert job.progress == pytest.approx(1.0)
