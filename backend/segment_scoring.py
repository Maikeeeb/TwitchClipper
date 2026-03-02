"""
Pure scoring and ranking logic for VOD segments.
"""

from __future__ import annotations

from backend.models.vod import Segment
from backend.scoring_common import (
    KeywordScoreConfig,
    compute_keyword_bonus,
    rank_by_keys,
    validate_non_negative_keyword_params,
)


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
    validate_non_negative_keyword_params(keyword_bonus, keyword_cap)

    bonus = compute_keyword_bonus(
        context_text,
        KeywordScoreConfig(
            keywords=keywords,
            keyword_bonus=keyword_bonus,
            keyword_cap=keyword_cap,
        ),
        # Keep segment behavior: ignore empty keyword entries.
        skip_empty_keywords=True,
    )

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
    validate_non_negative_keyword_params(keyword_bonus, keyword_cap)

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

    ranked = rank_by_keys(
        scored,
        lambda item: (-item[0], -item[2].spike_score, item[2].start_s, item[2].end_s, item[1]),
    )
    return [item[2] for item in ranked]
