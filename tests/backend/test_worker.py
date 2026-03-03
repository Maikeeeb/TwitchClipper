"""
Test Plan
- Partitions: run_next success, failure, no handler, empty queue; run_until_empty FIFO
- Boundaries: empty queue returns None; all jobs processed in order
- Failure modes: handler exception → FAILED; missing handler → FAILED

Covers: TODO-JOBS-003
"""

from datetime import datetime, timezone
import importlib

import pytest

from backend.job_queue import InMemoryJobQueue
from backend.models.jobs import JobStatus
from backend.worker import Worker, _default_clip_montage_handler


def _fixed_now() -> datetime:
    return datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_run_next_processes_job_success() -> None:
    """Validation: handler returns dict → job DONE, progress 1.0, result stored, error cleared."""
    queue = InMemoryJobQueue()
    job = queue.create_job("test_type", {"x": 1})
    queue.enqueue(job)
    worker = Worker(queue, handlers={"test_type": lambda j: {"ok": True}})
    now = _fixed_now()
    out = worker.run_next(now=now)
    assert out is job
    assert job.status == JobStatus.DONE
    assert job.progress == pytest.approx(1.0)
    assert job.finished_at == now
    assert job.result == {"ok": True}
    assert job.error is None


def test_run_next_processes_job_failure_exception() -> None:
    """Validation: handler raises → job FAILED, finished_at set, error contains message, result None."""

    def raise_boom(_j):
        raise ValueError("boom")

    queue = InMemoryJobQueue()
    job = queue.create_job("test_type")
    queue.enqueue(job)
    worker = Worker(queue, handlers={"test_type": raise_boom})
    now = _fixed_now()
    out = worker.run_next(now=now)
    assert out is job
    assert job.status == JobStatus.FAILED
    assert job.finished_at == now
    assert "boom" in (job.error or "")
    assert job.result is None


def test_run_next_no_handler_fails_job() -> None:
    """Validation: no handler for job type → FAILED with clear message."""
    queue = InMemoryJobQueue()
    job = queue.create_job("unknown_type")
    queue.enqueue(job)
    worker = Worker(queue, handlers={})
    now = _fixed_now()
    out = worker.run_next(now=now)
    assert out is job
    assert job.status == JobStatus.FAILED
    assert "No handler registered for job type: unknown_type" in (job.error or "")


def test_run_next_empty_queue_returns_none() -> None:
    """Boundary: run_next on empty queue returns None."""
    queue = InMemoryJobQueue()
    worker = Worker(queue, handlers={"test_type": lambda j: {}})
    now = _fixed_now()
    assert worker.run_next(now=now) is None


def test_run_until_empty_processes_all_fifo_order() -> None:
    """Validation: run_until_empty processes all enqueued jobs in FIFO order, returns list of 2 DONE."""
    queue = InMemoryJobQueue()
    j1 = queue.create_job("t1")
    j2 = queue.create_job("t2")
    queue.enqueue(j1)
    queue.enqueue(j2)
    worker = Worker(
        queue,
        handlers={
            "t1": lambda j: {"first": True},
            "t2": lambda j: {"second": True},
        },
    )
    now = _fixed_now()
    done = worker.run_until_empty(now=now)
    assert len(done) == 2
    assert done[0] is j1
    assert done[1] is j2
    assert j1.status == JobStatus.DONE and j1.result == {"first": True}
    assert j2.status == JobStatus.DONE and j2.result == {"second": True}


def test_default_clip_montage_handler_rejects_blank_streamer_names() -> None:
    """Defect: handler rejects whitespace-only names from non-API callers."""
    queue = InMemoryJobQueue()
    job = queue.create_job("clip_montage", {"streamer_names": ["   "], "current_videos_dir": "."})
    with pytest.raises(ValueError, match="at least one non-empty name"):
        _default_clip_montage_handler(job)


def test_default_clip_montage_handler_forwards_optional_pipeline_params(monkeypatch) -> None:
    """Validation: handler forwards clip montage tuning params to pipeline."""
    captured = {}
    pipeline = importlib.import_module("backend.pipeline")

    def _fake_scrape_filter_rank_download(streamer_names, current_videos_dir, **kwargs):
        captured["streamer_names"] = streamer_names
        captured["current_videos_dir"] = current_videos_dir
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr(pipeline, "scrape_filter_rank_download", _fake_scrape_filter_rank_download)
    queue = InMemoryJobQueue()
    job = queue.create_job(
        "clip_montage",
        {
            "streamer_names": ["alpha"],
            "current_videos_dir": "out",
            "max_clips": 7,
            "scrape_pool_size": 12,
            "per_streamer_k": 3,
            "apply_overlay": False,
        },
    )
    result = _default_clip_montage_handler(job)

    assert result == {"paths": [], "count": 0}
    assert captured["streamer_names"] == ["alpha"]
    assert captured["current_videos_dir"] == "out"
    assert captured["kwargs"]["max_clips"] == 7
    assert captured["kwargs"]["scrape_pool_size"] == 12
    assert captured["kwargs"]["per_streamer_k"] == 3
    assert captured["kwargs"]["apply_overlay"] is False

