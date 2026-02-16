"""
Test Plan
- Partitions: context matching/no-match, empty pipeline, spike->segment, merge, ranking, file-input flow
- Boundaries: context window behavior, deterministic message ordering
- Failure modes: no spike path and missing context handling

Covers: TODO-VOD-006
"""

import json
from pathlib import Path

import pytest

from backend.vod_chat_pipeline import (
    build_segment_contexts,
    chat_file_to_ranked_segments,
    chat_messages_to_ranked_segments,
)
from backend.vod_models import ChatMessage, Segment


def test_build_segment_contexts_matches_messages_in_window() -> None:
    """Messages inside expanded segment window are joined into context."""
    messages = [
        ChatMessage(timestamp_s=4.0, message="near"),
        ChatMessage(timestamp_s=20.0, message="far"),
        ChatMessage(timestamp_s=10.0, message="inside"),
    ]
    segments = [Segment(start_s=6.0, end_s=12.0, spike_score=3.0)]
    contexts = build_segment_contexts(messages, segments, context_window_s=2)
    assert contexts == {0: "near inside"}


def test_build_segment_contexts_no_matches_returns_empty_or_missing_key() -> None:
    """No matched messages omits segment key from context mapping."""
    messages = [ChatMessage(timestamp_s=100.0, message="away")]
    segments = [Segment(start_s=0.0, end_s=5.0, spike_score=1.0)]
    contexts = build_segment_contexts(messages, segments, context_window_s=1)
    assert 0 not in contexts
    assert contexts == {}


def test_build_segment_contexts_deterministic_order() -> None:
    """Joined message text preserves input message ordering."""
    messages = [
        ChatMessage(timestamp_s=5.0, message="first"),
        ChatMessage(timestamp_s=6.0, message="second"),
        ChatMessage(timestamp_s=5.5, message="third"),
    ]
    segments = [Segment(start_s=5.0, end_s=6.0, spike_score=2.0)]
    contexts = build_segment_contexts(messages, segments, context_window_s=0)
    assert contexts[0] == "first second third"


def test_chat_messages_to_ranked_segments_empty_returns_empty() -> None:
    """Empty message input short-circuits to empty segment output."""
    ranked = chat_messages_to_ranked_segments(
        [],
        bucket_seconds=10,
        min_count=2,
        padding_seconds=5,
    )
    assert ranked == []


def test_chat_messages_to_ranked_segments_generates_segments_from_spikes() -> None:
    """Spike buckets produce at least one segment with expected window shape."""
    messages = [
        ChatMessage(timestamp_s=10.1, message="a"),
        ChatMessage(timestamp_s=12.0, message="b"),
        ChatMessage(timestamp_s=14.5, message="c"),
    ]
    ranked = chat_messages_to_ranked_segments(
        messages,
        bucket_seconds=10,
        min_count=3,
        padding_seconds=5,
    )
    assert len(ranked) == 1
    assert ranked[0].start_s == pytest.approx(10.0)
    assert ranked[0].end_s == pytest.approx(20.0)


def test_chat_messages_to_ranked_segments_merges_overlaps() -> None:
    """Two nearby spikes that overlap after padding merge into one segment."""
    messages = [
        ChatMessage(timestamp_s=10.1, message="a"),
        ChatMessage(timestamp_s=11.0, message="b"),
        ChatMessage(timestamp_s=20.1, message="c"),
        ChatMessage(timestamp_s=21.0, message="d"),
    ]
    ranked = chat_messages_to_ranked_segments(
        messages,
        bucket_seconds=10,
        min_count=2,
        padding_seconds=10,
    )
    assert len(ranked) == 1
    assert ranked[0].start_s == pytest.approx(5.0)
    assert ranked[0].end_s == pytest.approx(35.0)


def test_chat_messages_to_ranked_segments_ranks_with_keyword_bonus() -> None:
    """Keyword match in segment context boosts ranking when spike scores tie."""
    messages = [
        ChatMessage(timestamp_s=10.2, message="noise"),
        ChatMessage(timestamp_s=11.0, message="normal"),
        ChatMessage(timestamp_s=41.1, message="POG play"),
        ChatMessage(timestamp_s=41.0, message="wow"),
    ]
    ranked = chat_messages_to_ranked_segments(
        messages,
        bucket_seconds=10,
        min_count=2,
        padding_seconds=4,
        context_window_s=0,
        keywords=["pog"],
        keyword_bonus=10.0,
        keyword_cap=10.0,
    )
    assert len(ranked) == 2
    assert ranked[0].start_s == pytest.approx(41.0)
    assert ranked[1].start_s == pytest.approx(11.0)


def test_chat_file_to_ranked_segments_jsonl(tmp_path: Path) -> None:
    """File-based helper loads JSONL and runs full glue pipeline."""
    path = tmp_path / "chat.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"timestamp_s": 10.0, "message": "x"}),
                json.dumps({"timestamp_s": 11.0, "message": "y"}),
            ]
        ),
        encoding="utf-8",
    )
    ranked = chat_file_to_ranked_segments(
        str(path),
        bucket_seconds=10,
        min_count=2,
        padding_seconds=3,
    )
    assert len(ranked) == 1
