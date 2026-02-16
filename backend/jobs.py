"""
Job model and states for the job queue system.

Minimal, stable job representation: status lifecycle (QUEUED -> RUNNING -> DONE/FAILED)
and optional result/error. No queue, worker, or persistence in this module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class JobStatus(Enum):
    """Job lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    """
    A single job with status, timestamps, optional result/error, and params.

    id: unique identifier (uuid4 string).
    type: job kind (e.g. "clip_montage").
    status: current state (default QUEUED).
    created_at: timezone-aware UTC time when the job was created.
    started_at / finished_at: set when job starts and when it completes.
    error: set on failure; cleared on success.
    progress: 0.0 to 1.0; succeed() sets to 1.0.
    result: output paths and metadata on success.
    params: inputs (e.g. streamer list) for the job.
    """

    type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    progress: float = 0.0
    result: Optional[dict[str, Any]] = None
    params: dict[str, Any] = field(default_factory=dict)

    def start(self, now: datetime) -> None:
        """
        Mark job as running and set started_at.

        Progress is unchanged (must remain >= 0).
        """
        self.status = JobStatus.RUNNING
        self.started_at = now

    def succeed(self, result: dict[str, Any], now: datetime) -> None:
        """
        Mark job as done, set finished_at, progress=1.0, store result, clear error.
        """
        self.status = JobStatus.DONE
        self.finished_at = now
        self.progress = 1.0
        self.result = result
        self.error = None

    def fail(self, error: str, now: datetime) -> None:
        """
        Mark job as failed, set finished_at and error; result remains None.
        """
        self.status = JobStatus.FAILED
        self.finished_at = now
        self.error = error
