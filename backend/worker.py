"""
Background worker: run queued jobs via registered handlers.

Single-threaded loop only. No persistence. Exceptions become FAILED jobs.
"""

from __future__ import annotations

import os
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


def _resolve_vod_url(job: Job) -> str:
    """Resolve vod_url from params, allowing vod_id as a fallback."""
    vod_url = job.params.get("vod_url")
    if isinstance(vod_url, str) and vod_url.strip():
        return vod_url.strip()

    vod_id = job.params.get("vod_id")
    if isinstance(vod_id, str) and vod_id.strip():
        return f"https://www.twitch.tv/videos/{vod_id.strip()}"

    raise ValueError("vod_highlights requires either 'vod_url' or 'vod_id'")


def _default_vod_highlights_handler(job: Job) -> dict:
    """
    Default handler for "vod_highlights" pipeline jobs.

    Expects params:
    - vod_url (or vod_id)
    - output_dir
    - optional keywords (list[str])
    - optional chat_path (for local import; otherwise chat is fetched via web endpoint)
    """
    from pathlib import Path

    from backend.vod_chat_fetch import fetch_vod_chat_to_jsonl
    from backend.vod_chat_pipeline import chat_file_to_ranked_segments
    from backend.vod_cut import cut_segments
    from backend.vod_download import download_vod
    from backend.vod_models import VodJobParams
    from backend.vod_montage import compile_vod_montage
    from backend.selection import select_non_overlapping_segments_for_duration

    vod_url = _resolve_vod_url(job)
    output_dir = job.params.get("output_dir", ".")
    keywords = job.params.get("keywords") or []
    if not isinstance(keywords, list):
        raise ValueError("keywords must be a list of strings when provided")

    spike_window_seconds = int(job.params.get("spike_window_seconds", 30))
    segment_padding_seconds = int(job.params.get("segment_padding_seconds", 15))
    min_count = int(job.params.get("min_count", 5))
    max_segment_seconds = float(job.params.get("max_segment_seconds", 120))
    diversity_windows = int(job.params.get("diversity_windows", 8))

    params = VodJobParams(
        vod_url=vod_url,
        output_dir=str(output_dir),
        keywords=[str(k) for k in keywords],
        spike_window_seconds=spike_window_seconds,
        segment_padding_seconds=segment_padding_seconds,
    )

    vod_asset = download_vod(params.vod_url, output_dir=params.output_dir)

    chat_path = job.params.get("chat_path")
    if chat_path is None:
        chat_output_path = Path(params.output_dir) / "chat.jsonl"
        chat_summary = fetch_vod_chat_to_jsonl(
            job.params.get("vod_id", params.vod_url),
            chat_output_path,
            max_pages=None,
        )
        chat_path = chat_summary.get("out_path") or str(chat_output_path)

    segments = chat_file_to_ranked_segments(
        str(chat_path),
        bucket_seconds=params.spike_window_seconds,
        min_count=min_count,
        padding_seconds=params.segment_padding_seconds,
        keywords=params.keywords,
    )

    selected_segments = select_non_overlapping_segments_for_duration(
        segments,
        max_segment_seconds=max_segment_seconds,
        diversity_windows=diversity_windows,
    )

    clips_dir = os.path.join(params.output_dir, "clips")
    clip_paths = cut_segments(
        vod_asset.vod_path,
        selected_segments,
        output_dir=clips_dir,
    )

    montage_path = os.path.join(params.output_dir, "montage.mp4")
    final_montage_path = compile_vod_montage(clip_paths, output_path=montage_path)

    return {
        "vod_path": vod_asset.vod_path,
        "chat_path": str(chat_path) if chat_path is not None else None,
        "segments_count": len(segments),
        "clips_count": len(clip_paths),
        "montage_path": final_montage_path,
        "clips_dir": clips_dir,
        "metadata_path": vod_asset.metadata_path,
        "durations_s": [segment.end_s - segment.start_s for segment in selected_segments],
    }


def default_handlers() -> dict[str, JobHandler]:
    """Built-in handlers. Register with Worker(queue, default_handlers())."""
    return {
        "clip_montage": _default_clip_montage_handler,
        "vod_highlights": _default_vod_highlights_handler,
    }


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
