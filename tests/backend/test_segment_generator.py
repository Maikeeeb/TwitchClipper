"""
Test Plan
- Partitions: empty/single/multi-spike generation and overlap/no-overlap merge paths
- Boundaries: invalid bucket/padding values, start clamping at 0, touching edges
- Failure modes: ensure merge preserves strongest spike and avoids input mutation

Covers: TODO-VOD-003
"""

import pytest

from backend.segment_generator import merge_overlapping_segments, spikes_to_segments
from backend.vod_models import Segment


def test_spikes_to_segments_empty_returns_empty() -> None:
    """Empty spike list returns no segments."""
    assert spikes_to_segments([], bucket_seconds=10, padding_seconds=5) == []


def test_spikes_to_segments_single_spike_generates_window() -> None:
    """Single spike becomes one centered segment window."""
    segments = spikes_to_segments([(10, 4)], bucket_seconds=10, padding_seconds=15)
    assert len(segments) == 1
    assert segments[0].start_s == pytest.approx(0.0)
    assert segments[0].end_s == pytest.approx(30.0)
    assert segments[0].spike_score == pytest.approx(4.0)
    assert segments[0].keyword_score == pytest.approx(0.0)


def test_spikes_to_segments_clamps_start_at_zero() -> None:
    """Start time is clamped to zero when padding pushes below 0."""
    segments = spikes_to_segments([(0, 2)], bucket_seconds=10, padding_seconds=10)
    assert len(segments) == 1
    assert segments[0].start_s == pytest.approx(0.0)
    assert segments[0].end_s == pytest.approx(15.0)


def test_spikes_to_segments_invalid_bucket_seconds_raises() -> None:
    """bucket_seconds must be positive."""
    with pytest.raises(ValueError, match="bucket_seconds"):
        spikes_to_segments([(0, 1)], bucket_seconds=0, padding_seconds=5)
    with pytest.raises(ValueError, match="bucket_seconds"):
        spikes_to_segments([(0, 1)], bucket_seconds=-1, padding_seconds=5)


def test_spikes_to_segments_invalid_padding_raises() -> None:
    """padding_seconds must be non-negative."""
    with pytest.raises(ValueError, match="padding_seconds"):
        spikes_to_segments([(0, 1)], bucket_seconds=10, padding_seconds=-1)


def test_spikes_to_segments_spike_score_equals_count() -> None:
    """Each segment spike_score is float(count)."""
    segments = spikes_to_segments([(0, 1), (10, 7), (20, 3)], bucket_seconds=10, padding_seconds=5)
    assert [segment.spike_score for segment in segments] == pytest.approx([1.0, 7.0, 3.0])


def test_merge_overlapping_segments_empty() -> None:
    """Merging empty list stays empty."""
    assert merge_overlapping_segments([]) == []


def test_merge_overlapping_segments_no_overlap_returns_same() -> None:
    """Non-overlapping segments are returned in sorted order unchanged."""
    segments = [
        Segment(start_s=20.0, end_s=30.0, spike_score=3.0),
        Segment(start_s=0.0, end_s=10.0, spike_score=1.0),
    ]
    merged = merge_overlapping_segments(segments)
    assert len(merged) == 2
    assert merged[0].start_s == pytest.approx(0.0)
    assert merged[0].end_s == pytest.approx(10.0)
    assert merged[1].start_s == pytest.approx(20.0)
    assert merged[1].end_s == pytest.approx(30.0)


def test_merge_overlapping_segments_overlaps_merge() -> None:
    """Overlapping segments merge into one wider segment."""
    segments = [
        Segment(start_s=0.0, end_s=10.0, spike_score=1.0),
        Segment(start_s=9.0, end_s=15.0, spike_score=2.0),
    ]
    merged = merge_overlapping_segments(segments)
    assert len(merged) == 1
    assert merged[0].start_s == pytest.approx(0.0)
    assert merged[0].end_s == pytest.approx(15.0)


def test_merge_overlapping_segments_touching_edges_merge() -> None:
    """Touching boundary (next.start == current.end) also merges."""
    segments = [
        Segment(start_s=0.0, end_s=10.0, spike_score=1.0),
        Segment(start_s=10.0, end_s=20.0, spike_score=2.0),
    ]
    merged = merge_overlapping_segments(segments)
    assert len(merged) == 1
    assert merged[0].start_s == pytest.approx(0.0)
    assert merged[0].end_s == pytest.approx(20.0)


def test_merge_overlapping_segments_keeps_max_spike_score() -> None:
    """Merged segment keeps strongest spike score from members."""
    segments = [
        Segment(start_s=0.0, end_s=10.0, spike_score=2.0),
        Segment(start_s=8.0, end_s=12.0, spike_score=7.0),
        Segment(start_s=11.0, end_s=15.0, spike_score=4.0),
    ]
    merged = merge_overlapping_segments(segments)
    assert len(merged) == 1
    assert merged[0].spike_score == pytest.approx(7.0)
    assert merged[0].keyword_score == pytest.approx(0.0)


def test_merge_overlapping_segments_does_not_mutate_input() -> None:
    """Input segments remain unchanged after merge."""
    original = [
        Segment(start_s=0.0, end_s=10.0, spike_score=1.0),
        Segment(start_s=9.0, end_s=12.0, spike_score=3.0),
    ]
    snapshot = [
        (segment.start_s, segment.end_s, segment.spike_score, segment.keyword_score)
        for segment in original
    ]
    _ = merge_overlapping_segments(original)
    after = [
        (segment.start_s, segment.end_s, segment.spike_score, segment.keyword_score)
        for segment in original
    ]
    assert after == snapshot


def test_merge_overlapping_segments_caps_merged_duration_to_120_seconds() -> None:
    """Overlapping chain is split when merge would exceed 120 seconds."""
    segments = [
        Segment(start_s=0.0, end_s=80.0, spike_score=3.0),
        Segment(start_s=70.0, end_s=150.0, spike_score=5.0),  # would make 150s if merged
    ]

    merged = merge_overlapping_segments(segments)
    assert len(merged) == 2
    assert (merged[0].end_s - merged[0].start_s) <= 120.0
    assert merged[0].start_s == pytest.approx(0.0)
    assert merged[0].end_s == pytest.approx(80.0)
    assert merged[1].start_s == pytest.approx(70.0)
    assert merged[1].end_s == pytest.approx(150.0)
