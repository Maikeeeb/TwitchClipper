"""
Duration-based clip selection for montage.

Selects ranked clips until total duration falls within [min_seconds, max_seconds].
"""

from __future__ import annotations

from backend.clip_models import ClipAsset

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
