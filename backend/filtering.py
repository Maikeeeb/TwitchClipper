"""
Clip filtering (metadata-only).

Deduplication by clip identity and optional max-per-streamer cap.
Uses ClipRef only; no ClipAsset, no file I/O.
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from backend.clip_models import ClipRef


def normalize_clip_url(url: str) -> str:
    """
    Normalize a clip URL for comparison.

    Removes query params (?...) and trailing slash.
    """
    if not url:
        return url
    parsed = urlparse(url)
    # Remove query and fragment
    normalized = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", "")
    )
    return normalized


def clip_identity(url: str) -> str:
    """
    Return a stable identity string for deduplication.

    Prefer: last path segment after '/clip/' if present.
    Fallback: normalized URL.
    """
    norm = normalize_clip_url(url)
    if "/clip/" in norm:
        segment = norm.split("/clip/")[-1].split("/")[0]
        if segment:
            return segment
    return norm


def filter_clips(
    clips: list[ClipRef],
    *,
    max_per_streamer: int | None = None,
) -> list[ClipRef]:
    """
    Filter and deduplicate clips by identity; optionally cap per streamer.

    - Deduplicate by clip_identity(clip_url). When duplicates exist, keep the
      clip with higher views (None treated as 0).
    - Preserve stable order: position follows first occurrence of each identity.
    - If max_per_streamer is set: keep at most N clips per streamer, preferring
      higher views; tie-break by clip_url. Streamer order follows first occurrence.
    - Does not mutate the input list.
    """
    if not clips:
        return []

    # Dedupe by identity: first-seen order, keep best (max views) per identity
    order: list[str] = []
    best: dict[str, ClipRef] = {}

    for ref in clips:
        ident = clip_identity(ref.clip_url)
        views_val = ref.views if ref.views is not None else 0
        if ident not in best or views_val > (best[ident].views or 0):
            best[ident] = ref
        if ident not in order:
            order.append(ident)

    deduped = [best[i] for i in order]

    if max_per_streamer is None:
        return deduped

    # Cap per streamer: preserve first-seen order of streamers; within each,
    # keep top max_per_streamer by views (tie-break clip_url).
    streamer_order: list[str] = []
    by_streamer: dict[str, list[ClipRef]] = {}
    for ref in deduped:
        s = ref.streamer if ref.streamer is not None else ""
        if s not in streamer_order:
            streamer_order.append(s)
        by_streamer.setdefault(s, []).append(ref)

    result: list[ClipRef] = []
    for s in streamer_order:
        group = by_streamer[s]
        # Sort by views desc (None->0), then clip_url asc; take first N
        group_sorted = sorted(
            group,
            key=lambda r: (-(r.views if r.views is not None else 0), r.clip_url),
        )
        result.extend(group_sorted[:max_per_streamer])

    return result
