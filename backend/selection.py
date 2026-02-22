"""
Duration-based clip selection for montage.

Selects ranked clips until total duration falls within [min_seconds, max_seconds].
"""

from __future__ import annotations

from backend.clip_models import ClipAsset
from backend.vod_models import Segment

MIN_MONTAGE_SECONDS = 8 * 60
MAX_MONTAGE_SECONDS = 10 * 60


def select_clips_for_duration(
    ranked_assets: list[ClipAsset],
    *,
    min_seconds: int,
    max_seconds: int,
) -> list[ClipAsset]:
    """
    Select clips in ranked order until total duration is in [min_seconds, max_seconds].

    - Skips clips where duration_s is None or <= 0.
    - Never exceeds max_seconds.
    - Stops early once total >= min_seconds.
    - If unable to reach min_seconds, returns best possible under max_seconds.
    - Does not mutate input list.
    """
    result: list[ClipAsset] = []
    total = 0.0
    for asset in ranked_assets:
        d = asset.duration_s
        if d is None or d <= 0:
            continue
        if total + d > max_seconds:
            continue
        result.append(asset)
        total += d
        if total >= min_seconds:
            break
    return result


def _segments_overlap(first: Segment, second: Segment) -> bool:
    """Return True when two segment windows overlap in VOD time."""
    return not (first.end_s <= second.start_s or second.end_s <= first.start_s)


def select_non_overlapping_segments_for_duration(
    ranked_segments: list[Segment],
    *,
    min_seconds: int = MIN_MONTAGE_SECONDS,
    max_seconds: int = MAX_MONTAGE_SECONDS,
    max_segment_seconds: float = 120.0,
    diversity_windows: int = 8,
) -> list[Segment]:
    """
    Greedily select ranked segments without overlap until duration target is reached.

    - Iterates best -> worst (input order).
    - Skips invalid/empty durations.
    - Rejects segments longer than max_segment_seconds.
    - Skips segments that overlap with already selected windows.
    - Never exceeds max_seconds.
    - First pass prefers timeline diversity (one pick per window).
    - Stops early once total >= min_seconds.
    """
    if max_segment_seconds <= 0:
        raise ValueError("max_segment_seconds must be > 0")
    if diversity_windows < 1:
        raise ValueError("diversity_windows must be >= 1")

    valid_ranked = [
        segment
        for segment in ranked_segments
        if 0 < (segment.end_s - segment.start_s) <= max_segment_seconds
    ]
    if not valid_ranked:
        return []

    timeline_end = max(segment.end_s for segment in valid_ranked)
    window_width = max(1.0, timeline_end / float(diversity_windows))

    def _window_idx(segment: Segment) -> int:
        return int(segment.start_s // window_width)

    selected: list[Segment] = []
    total = 0.0
    covered_windows: set[int] = set()
    selected_ids: set[int] = set()

    for require_new_window in (True, False):
        for segment in valid_ranked:
            segment_id = id(segment)
            if segment_id in selected_ids:
                continue
            if require_new_window and _window_idx(segment) in covered_windows:
                continue
            if any(_segments_overlap(segment, existing) for existing in selected):
                continue

            duration = segment.end_s - segment.start_s
            if total + duration > max_seconds:
                continue

            selected.append(segment)
            selected_ids.add(segment_id)
            covered_windows.add(_window_idx(segment))
            total += duration
            if total >= min_seconds:
                return selected

    return selected
