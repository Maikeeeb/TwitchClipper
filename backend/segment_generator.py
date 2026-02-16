"""
Pure segment window generation and merge logic for VOD spikes.
"""

from __future__ import annotations

from backend.vod_models import Segment


def spikes_to_segments(
    spikes: list[tuple[int, int]],
    *,
    bucket_seconds: int,
    padding_seconds: int,
) -> list[Segment]:
    """
    Convert spike buckets into segment windows around each spike center.
    """
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be > 0")
    if padding_seconds < 0:
        raise ValueError("padding_seconds must be >= 0")

    segments: list[Segment] = []
    for bucket_start_s, count in spikes:
        spike_center_s = bucket_start_s + (bucket_seconds / 2.0)
        start_s = max(0.0, spike_center_s - padding_seconds)
        end_s = spike_center_s + padding_seconds
        # Segment enforces end_s > start_s; keep a tiny positive width when padding is 0.
        if end_s <= start_s:
            end_s = start_s + 1e-9
        segments.append(
            Segment(
                start_s=start_s,
                end_s=end_s,
                spike_score=float(count),
            )
        )

    return sorted(segments, key=lambda segment: segment.start_s)


def merge_overlapping_segments(segments: list[Segment]) -> list[Segment]:
    """
    Merge segments that overlap or touch (next.start_s <= current.end_s).
    """
    if not segments:
        return []

    ordered = sorted(segments, key=lambda segment: segment.start_s)
    merged: list[Segment] = [
        Segment(
            start_s=ordered[0].start_s,
            end_s=ordered[0].end_s,
            spike_score=ordered[0].spike_score,
            keyword_score=0.0,
        )
    ]

    for next_segment in ordered[1:]:
        current = merged[-1]
        if next_segment.start_s <= current.end_s:
            merged[-1] = Segment(
                start_s=current.start_s,
                end_s=max(current.end_s, next_segment.end_s),
                spike_score=max(current.spike_score, next_segment.spike_score),
                keyword_score=0.0,
            )
            continue

        merged.append(
            Segment(
                start_s=next_segment.start_s,
                end_s=next_segment.end_s,
                spike_score=next_segment.spike_score,
                keyword_score=0.0,
            )
        )

    return merged
