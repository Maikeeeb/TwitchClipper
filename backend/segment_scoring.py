"""
Pure scoring and ranking logic for VOD segments.
"""

from __future__ import annotations

from backend.vod_models import Segment


def score_segment(
    segment: Segment,
    *,
    context_text: str | None = None,
    keywords: list[str] | None = None,
    keyword_bonus: float = 5.0,
    keyword_cap: float = 15.0,
) -> float:
    """
    Score a segment from spike strength plus optional capped keyword bonus.
    """
    if keyword_bonus < 0:
        raise ValueError("keyword_bonus must be >= 0")
    if keyword_cap < 0:
        raise ValueError("keyword_cap must be >= 0")

    bonus = 0.0
    if context_text is not None and keywords:
        haystack = context_text.lower()
        for keyword in keywords:
            if keyword and keyword.lower() in haystack:
                bonus += keyword_bonus
                if bonus >= keyword_cap:
                    bonus = keyword_cap
                    break

    return segment.spike_score + bonus


def rank_segments(
    segments: list[Segment],
    *,
    contexts: dict[int, str] | None = None,
    keywords: list[str] | None = None,
    keyword_bonus: float = 5.0,
    keyword_cap: float = 15.0,
) -> list[Segment]:
    """
    Return a new list ranked by total segment score descending.
    """
    if keyword_bonus < 0:
        raise ValueError("keyword_bonus must be >= 0")
    if keyword_cap < 0:
        raise ValueError("keyword_cap must be >= 0")

    contexts = contexts or {}

    scored: list[tuple[float, int, Segment]] = []
    for index, segment in enumerate(segments):
        context_text = contexts.get(index)
        total = score_segment(
            segment,
            context_text=context_text,
            keywords=keywords,
            keyword_bonus=keyword_bonus,
            keyword_cap=keyword_cap,
        )
        scored.append((total, index, segment))

    ranked = sorted(
        scored,
        key=lambda item: (-item[0], -item[2].spike_score, item[2].start_s, item[2].end_s, item[1]),
    )
    return [item[2] for item in ranked]
