"""
Test Plan
- Partitions: empty/single/multi-bucket and unsorted chat messages, spike filtering threshold
- Boundaries: bucket_seconds <= 0, min_count <= 0, timestamp on bucket edge
- Failure modes: defensive negative timestamp handling in bucketing

Covers: TODO-VOD-002
"""

import pytest

from backend.chat_spikes import bucket_chat_messages, detect_spikes
from backend.vod_models import ChatMessage


def _unsafe_chat_message(timestamp_s: float, message: str) -> ChatMessage:
    """
    Build ChatMessage without validation for defensive-path tests.
    """
    chat_message = object.__new__(ChatMessage)
    chat_message.timestamp_s = timestamp_s
    chat_message.message = message
    return chat_message


def test_bucket_chat_messages_empty_returns_empty() -> None:
    """Empty input has no buckets."""
    assert bucket_chat_messages([], bucket_seconds=10) == []


def test_bucket_chat_messages_single_message_bucketed() -> None:
    """Single message is assigned to its floor bucket start."""
    messages = [ChatMessage(timestamp_s=12.2, message="hi")]
    assert bucket_chat_messages(messages, bucket_seconds=10) == [(10, 1)]


def test_bucket_chat_messages_multiple_messages_same_bucket() -> None:
    """Multiple messages in same bucket are counted together."""
    messages = [
        ChatMessage(timestamp_s=2.0, message="a"),
        ChatMessage(timestamp_s=9.99, message="b"),
        ChatMessage(timestamp_s=0.1, message="c"),
    ]
    assert bucket_chat_messages(messages, bucket_seconds=10) == [(0, 3)]


def test_bucket_chat_messages_messages_across_buckets_sorted_output() -> None:
    """Messages across buckets produce sorted starts with correct counts."""
    messages = [
        ChatMessage(timestamp_s=0.0, message="a"),
        ChatMessage(timestamp_s=10.0, message="b"),
        ChatMessage(timestamp_s=19.9, message="c"),
        ChatMessage(timestamp_s=20.0, message="d"),
    ]
    assert bucket_chat_messages(messages, bucket_seconds=10) == [(0, 1), (10, 2), (20, 1)]


def test_bucket_chat_messages_unsorted_input_still_correct() -> None:
    """Input ordering does not change output counts/order."""
    messages = [
        ChatMessage(timestamp_s=21.0, message="d"),
        ChatMessage(timestamp_s=1.0, message="a"),
        ChatMessage(timestamp_s=14.0, message="c"),
        ChatMessage(timestamp_s=11.0, message="b"),
    ]
    assert bucket_chat_messages(messages, bucket_seconds=10) == [(0, 1), (10, 2), (20, 1)]


def test_bucket_chat_messages_bucket_seconds_must_be_positive() -> None:
    """bucket_seconds <= 0 is invalid."""
    messages = [ChatMessage(timestamp_s=1.0, message="x")]
    with pytest.raises(ValueError, match="bucket_seconds"):
        bucket_chat_messages(messages, bucket_seconds=0)
    with pytest.raises(ValueError, match="bucket_seconds"):
        bucket_chat_messages(messages, bucket_seconds=-5)


def test_bucket_chat_messages_negative_timestamp_raises_value_error() -> None:
    """Defensive: malformed message with negative timestamp is rejected."""
    bad = _unsafe_chat_message(timestamp_s=-1.0, message="bad")
    with pytest.raises(ValueError, match="timestamp_s"):
        bucket_chat_messages([bad], bucket_seconds=10)


def test_detect_spikes_filters_by_min_count() -> None:
    """Only buckets meeting threshold are returned."""
    buckets = [(0, 1), (10, 3), (20, 2), (30, 5)]
    assert detect_spikes(buckets, min_count=3) == [(10, 3), (30, 5)]


def test_detect_spikes_min_count_must_be_positive() -> None:
    """min_count must be >= 1."""
    buckets = [(0, 1)]
    with pytest.raises(ValueError, match="min_count"):
        detect_spikes(buckets, min_count=0)
    with pytest.raises(ValueError, match="min_count"):
        detect_spikes(buckets, min_count=-1)


def test_detect_spikes_preserves_order() -> None:
    """Filtered spikes keep the original bucket ordering."""
    buckets = [(0, 4), (10, 1), (20, 6), (30, 2)]
    assert detect_spikes(buckets, min_count=2) == [(0, 4), (20, 6), (30, 2)]
