"""
Test Plan
- Partitions: create_job, enqueue/dequeue, get, list_jobs, dedupe
- Boundaries: empty queue dequeue returns None; list_jobs with/without filter
- Failure modes: get unknown id returns None

Covers: TODO-JOBS-002
"""

from backend.job_queue import InMemoryJobQueue
from backend.jobs import Job, JobStatus


def test_create_job_stores_job_and_defaults_queued() -> None:
    """Validation: create_job creates Job with QUEUED status and stores it."""
    q = InMemoryJobQueue()
    job = q.create_job("clip_montage", {"streamers": ["a", "b"]})
    assert job.status == JobStatus.QUEUED
    assert job.type == "clip_montage"
    assert job.params == {"streamers": ["a", "b"]}
    assert q.get(job.id) is job
    assert job in q.list_jobs()


def test_create_job_params_defaults_to_empty_dict() -> None:
    """Boundary: create_job with no params uses {}."""
    q = InMemoryJobQueue()
    job = q.create_job("clip_montage")
    assert job.params == {}
    job2 = q.create_job("clip_montage", None)
    assert job2.params == {}


def test_enqueue_then_dequeue_fifo_order() -> None:
    """Validation: dequeue returns jobs in FIFO order."""
    q = InMemoryJobQueue()
    j1 = q.create_job("clip_montage")
    j2 = q.create_job("clip_montage")
    q.enqueue(j1)
    q.enqueue(j2)
    assert q.dequeue() is j1
    assert q.dequeue() is j2
    assert q.dequeue() is None


def test_dequeue_empty_returns_none() -> None:
    """Boundary: dequeue on empty queue returns None."""
    q = InMemoryJobQueue()
    assert q.dequeue() is None


def test_get_returns_job_by_id() -> None:
    """Validation: get returns Job by id."""
    q = InMemoryJobQueue()
    job = q.create_job("clip_montage")
    assert q.get(job.id) is job
    assert q.get("nonexistent") is None


def test_list_jobs_filters_by_status() -> None:
    """Validation: list_jobs with status filter returns only matching jobs."""
    q = InMemoryJobQueue()
    j1 = q.create_job("clip_montage")
    j2 = q.create_job("clip_montage")
    q.enqueue(j1)
    q.enqueue(j2)
    j1.status = JobStatus.RUNNING
    all_jobs = q.list_jobs()
    assert len(all_jobs) == 2
    queued = q.list_jobs(JobStatus.QUEUED)
    assert len(queued) == 1
    assert queued[0] is j2
    running = q.list_jobs(JobStatus.RUNNING)
    assert len(running) == 1
    assert running[0] is j1


def test_enqueue_does_not_duplicate_same_job() -> None:
    """Validation: enqueue same job twice does not add it twice to queue."""
    q = InMemoryJobQueue()
    job = q.create_job("clip_montage")
    q.enqueue(job)
    q.enqueue(job)
    q.enqueue(job)
    first = q.dequeue()
    second = q.dequeue()
    assert first is job
    assert second is None
