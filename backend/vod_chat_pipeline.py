"""
Glue pipeline for converting chat messages into ranked highlight segments.
"""

from __future__ import annotations

from backend.chat_import import load_chat_messages
from backend.chat_spikes import bucket_chat_messages, detect_spikes
from backend.segment_generator import merge_overlapping_segments, spikes_to_segments
from backend.segment_scoring import rank_segments
from backend.vod_models import ChatMessage, Segment


def build_segment_contexts(
    messages: list[ChatMessage],
    segments: list[Segment],
    *,
    context_window_s: int = 10,
) -> dict[int, str]:
    """
    Build index->context mapping by joining messages near each segment window.
    """
    if context_window_s < 0:
        raise ValueError("context_window_s must be >= 0")

    contexts: dict[int, str] = {}
    for idx, segment in enumerate(segments):
        lower = segment.start_s - context_window_s
        upper = segment.end_s + context_window_s
        matched = [
            message.message
            for message in messages
            if lower <= message.timestamp_s <= upper
        ]
        if matched:
            contexts[idx] = " ".join(matched)
    return contexts


def chat_messages_to_ranked_segments(
    messages: list[ChatMessage],
    *,
    bucket_seconds: int,
    min_count: int,
    padding_seconds: int,
    context_window_s: int = 10,
    keywords: list[str] | None = None,
    keyword_bonus: float = 5.0,
    keyword_cap: float = 15.0,
) -> list[Segment]:
    """
    Convert chat messages to merged + ranked segment candidates.
    """
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be > 0")
    if min_count < 1:
        raise ValueError("min_count must be >= 1")
    if padding_seconds < 0:
        raise ValueError("padding_seconds must be >= 0")
    if context_window_s < 0:
        raise ValueError("context_window_s must be >= 0")
    if not messages:
        return []

    buckets = bucket_chat_messages(messages, bucket_seconds=bucket_seconds)
    spikes = detect_spikes(buckets, min_count=min_count)
    segments = spikes_to_segments(
        spikes,
        bucket_seconds=bucket_seconds,
        padding_seconds=padding_seconds,
    )
    merged = merge_overlapping_segments(segments)
    contexts = build_segment_contexts(
        messages,
        merged,
        context_window_s=context_window_s,
    )
    return rank_segments(
        merged,
        contexts=contexts,
        keywords=keywords,
        keyword_bonus=keyword_bonus,
        keyword_cap=keyword_cap,
    )


def chat_file_to_ranked_segments(
    path: str,
    *,
    bucket_seconds: int,
    min_count: int,
    padding_seconds: int,
    context_window_s: int = 10,
    keywords: list[str] | None = None,
    keyword_bonus: float = 5.0,
    keyword_cap: float = 15.0,
) -> list[Segment]:
    """
    Load chat log from file and produce ranked segment candidates.
    """
    messages = load_chat_messages(path)
    return chat_messages_to_ranked_segments(
        messages,
        bucket_seconds=bucket_seconds,
        min_count=min_count,
        padding_seconds=padding_seconds,
        context_window_s=context_window_s,
        keywords=keywords,
        keyword_bonus=keyword_bonus,
        keyword_cap=keyword_cap,
    )
