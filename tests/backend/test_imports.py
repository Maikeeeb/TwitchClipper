"""
Test Plan
- Partitions: module import and callable exposure
- Boundaries: none
- Failure modes: missing attributes break import validation
"""

from backend import clips
from backend import clip_models
from backend import filtering
from backend import job_queue
from backend import jobs
from backend import oneVideo
from backend import pipeline
from backend import selection
from backend import worker


def test_backend_modules_importable() -> None:
    # Covers: TODO-TEST-IMPORTS
    assert callable(clips.getclips)
    assert callable(clips.download_clip)
    assert callable(oneVideo.compile)
    assert hasattr(clip_models, "ClipRef")
    assert hasattr(clip_models, "ClipAsset")
    assert callable(clip_models.parse_views)
    assert callable(filtering.filter_clips)
    assert callable(filtering.normalize_clip_url)
    assert callable(filtering.clip_identity)
    assert callable(pipeline.scrape_filter_rank_download)
    assert pipeline.DEFAULT_MAX_CLIPS == 20
    assert callable(selection.select_clips_for_duration)
    assert isinstance(pipeline.PER_STREAMER_K, int) and pipeline.PER_STREAMER_K > 0
    assert hasattr(jobs, "Job") and hasattr(jobs, "JobStatus")
    assert jobs.JobStatus.QUEUED is not None
    assert callable(getattr(jobs.Job, "start")) and callable(getattr(jobs.Job, "succeed"))
    assert hasattr(job_queue, "InMemoryJobQueue")
    assert hasattr(worker, "Worker")
    assert callable(getattr(worker.Worker, "run_next"))
    assert callable(getattr(worker.Worker, "run_until_empty"))
