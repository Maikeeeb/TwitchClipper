"""
Pure chat spike detection logic for VOD highlights.

This module intentionally provides deterministic, in-memory computations only.
"""

from __future__ import annotations

import math
from collections import defaultdict

from backend.vod_models import ChatMessage


def bucket_chat_messages(
    messages: list[ChatMessage],
    *,
    bucket_seconds: int,
) -> list[tuple[int, int]]:
    """
    Group chat messages into fixed-width second buckets.

    Returns sorted (bucket_start_s, count) pairs.
    """
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be > 0")

    counts_by_bucket: dict[int, int] = defaultdict(int)
    for message in messages:
        if message.timestamp_s < 0:
            raise ValueError("message timestamp_s must be >= 0")
        bucket_index = math.floor(message.timestamp_s / bucket_seconds)
        bucket_start_s = bucket_index * bucket_seconds
        counts_by_bucket[bucket_start_s] += 1

    return sorted(counts_by_bucket.items(), key=lambda item: item[0])


def detect_spikes(
    buckets: list[tuple[int, int]],
    *,
    min_count: int,
) -> list[tuple[int, int]]:
    """Return buckets where message count is at least min_count."""
    if min_count < 1:
        raise ValueError("min_count must be >= 1")
    return [bucket for bucket in buckets if bucket[1] >= min_count]
