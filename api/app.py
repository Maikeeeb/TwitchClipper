"""
FastAPI app for the job system.

Lives in api/app.py. Uses backend modules only; no backend logic here.
Run: uvicorn api.app:app --reload
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from backend.config import (
    API_DEFAULT_SEGMENT_PADDING_SECONDS,
    API_DEFAULT_VOD_MIN_COUNT,
    DEFAULT_CURRENT_VIDEOS_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_OUTPUT_DIR,
    env_bool,
)
from backend.db.repo import SQLiteJobRepository
from backend.job_queue import InMemoryJobQueue
from backend.models.jobs import Job
from backend.worker import Worker, default_handlers


# --- Request/Response models ---


class ClipMontageJobRequest(BaseModel):
    """Request body for POST /jobs/clip-montage."""

    streamer_names: list[str] = Field(..., min_length=1, description="At least one streamer")
    current_videos_dir: str = DEFAULT_CURRENT_VIDEOS_DIR
    apply_overlay: bool = False
    max_clips: Optional[int] = Field(None, ge=0)
    scrape_pool_size: Optional[int] = Field(None, ge=0)
    per_streamer_k: Optional[int] = Field(None, ge=0)

    @field_validator("streamer_names")
    @classmethod
    def validate_streamer_names(cls, value: list[str]) -> list[str]:
        cleaned = [name.strip() for name in value]
        if any(not name for name in cleaned):
            raise ValueError("streamer_names must not contain empty/whitespace-only values")
        return cleaned


class VodHighlightsJobRequest(BaseModel):
    """Request body for POST /jobs/vod-highlights."""

    vod_url: str = Field(..., min_length=1, description="Twitch VOD URL or local path")
    output_dir: str = DEFAULT_OUTPUT_DIR
    keywords: list[str] = Field(default_factory=list)
    chat_path: Optional[str] = None
    min_count: int = Field(API_DEFAULT_VOD_MIN_COUNT, ge=1)
    spike_window_seconds: int = Field(30, gt=0)
    segment_padding_seconds: int = Field(API_DEFAULT_SEGMENT_PADDING_SECONDS, ge=0)
    max_segment_seconds: float = Field(120, gt=0)
    diversity_windows: int = Field(8, ge=1)


class JobSubmitRequest(BaseModel):
    """Generic request body for POST /jobs."""

    type: str = Field(..., min_length=1, description="Job type")
    params: dict[str, Any] = Field(default_factory=dict, description="Job params")


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
    outputs: Optional[dict[str, Any]] = None
    params: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_job(cls, job: Job, *, outputs: Optional[dict[str, Any]] = None) -> "JobResponse":
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
            outputs=outputs,
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


def get_job_repo(request: Request) -> Optional[SQLiteJobRepository]:
    return request.app.state.job_repo


def _build_optional_job_repo(
    *,
    job_repo: Optional[SQLiteJobRepository],
    db_enabled: Optional[bool],
    db_path: Optional[str],
) -> Optional[SQLiteJobRepository]:
    if job_repo is not None:
        return job_repo

    enabled = (
        db_enabled
        if db_enabled is not None
        else env_bool("TWITCHCLIPPER_DB_ENABLED", default=False)
    )
    if not enabled:
        return None

    path = db_path or os.getenv("TWITCHCLIPPER_DB_PATH", DEFAULT_DB_PATH)
    return SQLiteJobRepository(path)


# --- App factory ---


def create_app(
    queue: Optional[InMemoryJobQueue] = None,
    handlers: Optional[dict[str, Any]] = None,
    job_repo: Optional[SQLiteJobRepository] = None,
    db_enabled: Optional[bool] = None,
    db_path: Optional[str] = None,
) -> FastAPI:
    """
    Build FastAPI app. Default: in-memory queue and default_handlers().
    Tests can pass queue and handlers to avoid real pipeline and control state.
    """
    app = FastAPI(title="TwitchClipper API")
    app.state.queue = queue if queue is not None else InMemoryJobQueue()
    app.state.job_repo = _build_optional_job_repo(
        job_repo=job_repo,
        db_enabled=db_enabled,
        db_path=db_path,
    )
    app.state.worker = Worker(
        app.state.queue,
        handlers or default_handlers(),
        job_repo=app.state.job_repo,
    )

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/jobs/clip-montage")
    def submit_clip_montage(
        body: ClipMontageJobRequest,
        queue: InMemoryJobQueue = Depends(get_queue),
        job_repo: Optional[SQLiteJobRepository] = Depends(get_job_repo),
    ) -> dict[str, str]:
        params = body.model_dump()
        job = queue.create_job("clip_montage", params)
        if job_repo is not None:
            job_repo.create_job(job)
        queue.enqueue(job)
        return {"job_id": job.id}

    @app.post("/jobs/vod-highlights")
    def submit_vod_highlights(
        body: VodHighlightsJobRequest,
        queue: InMemoryJobQueue = Depends(get_queue),
        job_repo: Optional[SQLiteJobRepository] = Depends(get_job_repo),
    ) -> dict[str, str]:
        params = body.model_dump()
        job = queue.create_job("vod_highlights", params)
        if job_repo is not None:
            job_repo.create_job(job)
        queue.enqueue(job)
        return {"job_id": job.id}

    @app.post("/jobs")
    def submit_job(
        body: JobSubmitRequest,
        queue: InMemoryJobQueue = Depends(get_queue),
        job_repo: Optional[SQLiteJobRepository] = Depends(get_job_repo),
    ) -> dict[str, str]:
        job = queue.create_job(body.type, body.params)
        if job_repo is not None:
            job_repo.create_job(job)
        queue.enqueue(job)
        return {"job_id": job.id}

    # Future: GET /jobs to list jobs (e.g. with optional status filter).
    @app.get("/jobs/{job_id}", response_model=JobResponse)
    def get_job(
        job_id: str,
        queue: InMemoryJobQueue = Depends(get_queue),
        job_repo: Optional[SQLiteJobRepository] = Depends(get_job_repo),
    ) -> JobResponse:
        # Single source of truth rule:
        # - DB enabled: status/result reads come from SQLite.
        # - DB disabled: reads come from in-memory queue storage.
        if job_repo is not None:
            job = job_repo.get_job(job_id)
            outputs = job_repo.get_job_outputs(job_id)
        else:
            job = queue.get(job_id)
            outputs = None
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse.from_job(job, outputs=outputs)

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
