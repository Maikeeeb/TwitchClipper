"""
Pipeline: scrape, filter, rank, download top N clips.

Used by the CLI. Kept separate for testability.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from backend.clip_models import ClipRef
from backend.clips import download_clip, getclips, overlay
from backend.filtering import filter_clips
from backend.scoring import rank_clips
from backend.selection import (
    MAX_MONTAGE_SECONDS,
    MIN_MONTAGE_SECONDS,
    select_clips_for_duration,
)

# Download pool limit (how many clips to download); final selection is duration-based (8–10 min).
DEFAULT_MAX_CLIPS = 20
# Scrape pool per streamer before filter/rank; may be renamed DEFAULT_SCRAPE_LIMIT later.
SCRAPE_POOL_SIZE = 50
# Max candidates per streamer before global rank (multi-streamer only).
PER_STREAMER_K = 10


def select_per_streamer_candidates(
    streamer_names: list[str],
    current_videos_dir: str,
    *,
    scrape_pool_size: int,
    per_streamer_k: int,
    now: datetime,
) -> list[ClipRef]:
    """
    For each streamer: scrape, filter, rank, take top K. Combine in streamer order.

    Returns combined list of ClipRef (first-seen streamer order).
    """
    combined: list[ClipRef] = []
    for name in streamer_names:
        refs = getclips(
            name,
            current_videos_dir=current_videos_dir,
            max_clips=scrape_pool_size,
            download=False,
        )
        refs = filter_clips(refs)
        refs = rank_clips(refs, now=now)
        refs = refs[:per_streamer_k]
        combined.extend(refs)
    return combined


def scrape_filter_rank_download(
    streamer_names: list[str],
    current_videos_dir: str,
    *,
    apply_overlay: bool = True,
    max_clips: int = DEFAULT_MAX_CLIPS,
    scrape_pool_size: int = SCRAPE_POOL_SIZE,
    per_streamer_k: int = PER_STREAMER_K,
) -> list:
    """
    Scrape clips from streamers, filter, rank, take top N, download.

    Multi-streamer: per-streamer selection (top K each) then global filter/rank.
    Single-streamer: same behavior (K = scrape_pool_size so no per-streamer cap).
    Returns list of ClipAsset. Does not mutate input streamer_names.
    """
    now = datetime.now(timezone.utc)
    if len(streamer_names) > 1:
        k = per_streamer_k
    else:
        k = scrape_pool_size  # single streamer: no per-streamer cap
    candidates = select_per_streamer_candidates(
        streamer_names,
        current_videos_dir,
        scrape_pool_size=scrape_pool_size,
        per_streamer_k=k,
        now=now,
    )
    refs = filter_clips(candidates)
    refs = rank_clips(refs, now=now)
    refs = refs[:max_clips]
    assets = []
    for ref in refs:
        asset = download_clip(ref, output_dir=current_videos_dir)
        assets.append(asset)
    selected = select_clips_for_duration(
        assets,
        min_seconds=MIN_MONTAGE_SECONDS,
        max_seconds=MAX_MONTAGE_SECONDS,
    )
    if selected and apply_overlay:
        # Overlay is applied to the top-ranked clip; ranking changes → overlay target changes.
        first = selected[0].clip_ref
        view_str = str(first.views) if first.views is not None else "0"
        overlay(view_str, first.streamer or "", current_videos_dir)
        first_path = selected[0].output_path
        if os.path.exists(first_path):
            os.remove(first_path)
    return selected
