"""
Background worker: run queued jobs via registered handlers.

Single-threaded loop only. No persistence. Exceptions become FAILED jobs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from backend.job_queue import InMemoryJobQueue
from backend.jobs import Job, JobStatus

# Handler for a job type: receives Job, returns result dict.
JobHandler = Callable[[Job], dict]


def _default_clip_montage_handler(job: Job) -> dict:
    """
    Minimal handler for "clip_montage": calls pipeline.scrape_filter_rank_download.

    Expects job.params: streamer_names (list[str]), current_videos_dir (str).
    Returns dict with paths and count for job result.
    """
    from backend import pipeline

    streamer_names = job.params.get("streamer_names") or []
    current_videos_dir = job.params.get("current_videos_dir", ".")
    if not streamer_names:
        return {"paths": [], "count": 0}
    selected = pipeline.scrape_filter_rank_download(
        list(streamer_names),
        current_videos_dir,
    )
    paths = [a.output_path for a in selected]
    return {"paths": paths, "count": len(paths)}


def default_handlers() -> dict[str, JobHandler]:
    """Built-in handlers. Register with Worker(queue, default_handlers())."""
    return {"clip_montage": _default_clip_montage_handler}


class Worker:
    """
    Runs queued jobs using a handler per job type.

    run_next processes one job; run_until_empty processes all.
    Missing handler or handler exception → job marked FAILED, process does not crash.
    """

    def __init__(
        self,
        queue: InMemoryJobQueue,
        handlers: dict[str, JobHandler] | None = None,
    ) -> None:
        self.queue = queue
        self.handlers = handlers if handlers is not None else {}

    def run_next(self, *, now: datetime) -> Job | None:
        """
        Dequeue one job, run its handler, update status/result/error, return the job.

        Returns None if queue is empty.
        """
        job = self.queue.dequeue()
        if job is None:
            return None
        job.start(now)
        handler = self.handlers.get(job.type)
        if handler is None:
            job.fail(f"No handler registered for job type: {job.type}", now)
            return job
        try:
            result = handler(job)
            job.succeed(result, now)
        except Exception as e:
            job.fail(str(e), now)
        return job

    def run_until_empty(self, *, now: datetime) -> list[Job]:
        """Repeatedly run_next until queue is empty. Returns list of processed jobs."""
        done: list[Job] = []
        while True:
            job = self.run_next(now=now)
            if job is None:
                break
            done.append(job)
        return done
