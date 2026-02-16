"""
FastAPI app for the job system.

Lives in api/app.py. Uses backend modules only; no backend logic here.
Run: uvicorn api.app:app --reload
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from backend.job_queue import InMemoryJobQueue
from backend.jobs import Job
from backend.worker import Worker, default_handlers


# --- Request/Response models ---


class ClipMontageJobRequest(BaseModel):
    """Request body for POST /jobs/clip-montage."""

    streamer_names: list[str] = Field(..., min_length=1, description="At least one streamer")
    current_videos_dir: str = "."
    apply_overlay: bool = False
    max_clips: Optional[int] = Field(None, ge=0)
    scrape_pool_size: Optional[int] = Field(None, ge=0)
    per_streamer_k: Optional[int] = Field(None, ge=0)


class JobResponse(BaseModel):
    """Response for GET /jobs/{job_id}."""

    id: str
    type: str
    status: str
    progress: float
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    params: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_job(cls, job: Job) -> "JobResponse":
        def iso(d: Optional[datetime]) -> Optional[str]:
            return d.isoformat() if d is not None else None

        return cls(
            id=job.id,
            type=job.type,
            status=job.status.value,
            progress=job.progress,
            created_at=iso(job.created_at),
            started_at=iso(job.started_at),
            finished_at=iso(job.finished_at),
            error=job.error,
            result=job.result,
            params=job.params,
        )


# --- Dependencies (injectable for tests) ---


def get_now() -> datetime:
    """Current time for run_next. Override in tests for determinism."""
    return datetime.now(timezone.utc)


def get_queue(request: Request) -> InMemoryJobQueue:
    return request.app.state.queue


def get_worker(request: Request) -> Worker:
    return request.app.state.worker


# --- App factory ---


def create_app(
    queue: Optional[InMemoryJobQueue] = None,
    handlers: Optional[dict[str, Any]] = None,
) -> FastAPI:
    """
    Build FastAPI app. Default: in-memory queue and default_handlers().
    Tests can pass queue and handlers to avoid real pipeline and control state.
    """
    app = FastAPI(title="TwitchClipper API")
    app.state.queue = queue if queue is not None else InMemoryJobQueue()
    app.state.worker = Worker(app.state.queue, handlers or default_handlers())

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/jobs/clip-montage")
    def submit_clip_montage(
        body: ClipMontageJobRequest,
        queue: InMemoryJobQueue = Depends(get_queue),
    ) -> dict[str, str]:
        params = body.model_dump()
        job = queue.create_job("clip_montage", params)
        queue.enqueue(job)
        return {"job_id": job.id}

    # Future: GET /jobs to list jobs (e.g. with optional status filter).
    @app.get("/jobs/{job_id}", response_model=JobResponse)
    def get_job(
        job_id: str,
        queue: InMemoryJobQueue = Depends(get_queue),
    ) -> JobResponse:
        job = queue.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse.from_job(job)

    # Dev helper: process one queued job. Remove or mark dev-only when a real worker process exists.
    @app.post("/jobs/run-next")
    def run_next(
        queue: InMemoryJobQueue = Depends(get_queue),
        worker: Worker = Depends(get_worker),
        now: datetime = Depends(get_now),
    ) -> dict[str, Any]:
        job = worker.run_next(now=now)
        if job is None:
            return {"processed": 0}
        return {
            "processed": 1,
            "job_id": job.id,
            "status": job.status.value,
        }

    return app


# Default app instance (used by uvicorn api.app:app)
app = create_app()
