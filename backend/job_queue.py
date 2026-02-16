"""
In-memory job queue: create, enqueue, dequeue, lookup.

No threading, async, or worker loop. FIFO order with deduplicate on enqueue.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from backend.jobs import Job, JobStatus


class InMemoryJobQueue:
    """
    In-memory FIFO job queue with storage and lookup.

    Jobs are stored by id. Queue order is managed separately.
    Enqueue does not duplicate a job already in the queue.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._queue: deque[str] = deque()
        self._queued_ids: set[str] = set()

    def create_job(self, job_type: str, params: dict | None = None) -> Job:
        """
        Create a Job with status QUEUED and store it.

        params defaults to {}.
        Returns the created Job.
        """
        p = params if params is not None else {}
        job = Job(type=job_type, params=p)
        self._jobs[job.id] = job
        return job

    def enqueue(self, job: Job) -> None:
        """
        Add job id to FIFO queue order.

        If job id is already in the queue, does nothing (no duplicate).
        Stores the job if not yet stored.
        """
        self._jobs[job.id] = job
        if job.id in self._queued_ids:
            return
        self._queued_ids.add(job.id)
        self._queue.append(job.id)

    def dequeue(self) -> Job | None:
        """
        Pop next job id FIFO and return the Job.

        Returns None if queue is empty.
        Does not mutate job status (worker handles RUNNING).
        """
        if not self._queue:
            return None
        job_id = self._queue.popleft()
        self._queued_ids.discard(job_id)
        return self._jobs.get(job_id)

    def get(self, job_id: str) -> Job | None:
        """Return Job by id, or None if not found."""
        return self._jobs.get(job_id)

    def list_jobs(self, status: JobStatus | None = None) -> list[Job]:
        """
        Return all jobs, optionally filtered by status.
        """
        jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        return jobs
