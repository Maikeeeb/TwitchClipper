"""
Test Plan
- Partitions: base scoring, keyword bonus, cap behavior, ranking with/without contexts
- Boundaries: none/empty keyword inputs, missing context indexes, negative bonus/cap values
- Failure modes: invalid scoring params raise, ranking remains stable and non-mutating

Covers: TODO-VOD-004
"""

from datetime import datetime, timezone

import pytest

from backend.models.clips import ClipRef
from backend.models.vod import Segment
from backend.scoring import score_clip
from backend.segment_scoring import rank_segments, score_segment

FIXED_NOW = datetime(2025, 2, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_score_segment_base_is_spike_score() -> None:
    """Without keyword inputs, score is spike score only."""
    segment = Segment(start_s=0.0, end_s=5.0, spike_score=12.0)
    assert score_segment(segment) == pytest.approx(12.0)


def test_score_segment_keyword_bonus_applies_case_insensitive() -> None:
    """Keyword matches are case-insensitive substring checks."""
    segment = Segment(start_s=0.0, end_s=5.0, spike_score=10.0)
    score = score_segment(
        segment,
        context_text="Huge POG moment with wow reactions",
        keywords=["pog", "WOW"],
        keyword_bonus=2.5,
    )
    assert score == pytest.approx(15.0)


def test_score_segment_keyword_bonus_capped() -> None:
    """Total keyword bonus is capped by keyword_cap."""
    segment = Segment(start_s=0.0, end_s=5.0, spike_score=3.0)
    score = score_segment(
        segment,
        context_text="a b c d e",
        keywords=["a", "b", "c", "d", "e"],
        keyword_bonus=5.0,
        keyword_cap=12.0,
    )
    assert score == pytest.approx(15.0)


def test_score_segment_handles_none_context_or_keywords() -> None:
    """None/empty inputs for context/keywords should not crash or add bonus."""
    segment = Segment(start_s=0.0, end_s=5.0, spike_score=7.0)
    assert score_segment(segment, context_text=None, keywords=["x"]) == pytest.approx(7.0)
    assert score_segment(segment, context_text="x", keywords=None) == pytest.approx(7.0)
    assert score_segment(segment, context_text="x", keywords=[]) == pytest.approx(7.0)


def test_score_segment_rejects_negative_bonus_or_cap() -> None:
    """Negative bonus or cap values are invalid."""
    segment = Segment(start_s=0.0, end_s=5.0, spike_score=1.0)
    with pytest.raises(ValueError, match="keyword_bonus"):
        score_segment(segment, keyword_bonus=-0.1)
    with pytest.raises(ValueError, match="keyword_cap"):
        score_segment(segment, keyword_cap=-1.0)


def test_rank_segments_sorts_by_score_desc() -> None:
    """Higher total score ranks first."""
    segments = [
        Segment(start_s=0.0, end_s=5.0, spike_score=4.0),
        Segment(start_s=10.0, end_s=15.0, spike_score=6.0),
        Segment(start_s=20.0, end_s=25.0, spike_score=5.0),
    ]
    contexts = {0: "pog", 1: "", 2: "pog"}
    ranked = rank_segments(segments, contexts=contexts, keywords=["pog"], keyword_bonus=5.0)
    assert ranked == [segments[2], segments[0], segments[1]]


def test_rank_segments_tie_break_spike_score() -> None:
    """If totals tie, higher spike_score comes first."""
    first = Segment(start_s=0.0, end_s=5.0, spike_score=10.0)
    second = Segment(start_s=1.0, end_s=6.0, spike_score=8.0)
    ranked = rank_segments(
        [second, first],
        contexts={0: "pog", 1: ""},
        keywords=["pog"],
        keyword_bonus=2.0,
    )
    assert ranked == [first, second]


def test_rank_segments_tie_break_start_time() -> None:
    """If score/spike tie, earlier start_s then earlier end_s wins."""
    later = Segment(start_s=10.0, end_s=20.0, spike_score=5.0)
    earlier = Segment(start_s=5.0, end_s=25.0, spike_score=5.0)
    same_start_longer = Segment(start_s=5.0, end_s=30.0, spike_score=5.0)
    ranked = rank_segments([later, same_start_longer, earlier])
    assert ranked == [earlier, same_start_longer, later]


def test_rank_segments_final_tie_break_preserves_input_index() -> None:
    """If all tie keys match, original input index is the final tie-break."""
    first = Segment(start_s=5.0, end_s=15.0, spike_score=3.0)
    second = Segment(start_s=5.0, end_s=15.0, spike_score=3.0)
    ranked = rank_segments([second, first])
    assert ranked == [second, first]


def test_rank_segments_does_not_mutate_input() -> None:
    """Input list order stays unchanged after ranking call."""
    segments = [
        Segment(start_s=10.0, end_s=15.0, spike_score=1.0),
        Segment(start_s=0.0, end_s=5.0, spike_score=2.0),
    ]
    snapshot = list(segments)
    _ = rank_segments(segments)
    assert segments == snapshot


def test_rank_segments_contexts_by_index_work() -> None:
    """Keyword bonuses map by input index, not by segment timestamps."""
    segments = [
        Segment(start_s=100.0, end_s=110.0, spike_score=2.0),
        Segment(start_s=0.0, end_s=10.0, spike_score=2.0),
    ]
    ranked = rank_segments(
        segments,
        contexts={1: "amazing pog"},
        keywords=["pog"],
        keyword_bonus=3.0,
    )
    assert ranked[0] is segments[1]


def test_rank_segments_missing_context_index_safe() -> None:
    """Missing context entries are treated as None."""
    segments = [
        Segment(start_s=0.0, end_s=10.0, spike_score=3.0),
        Segment(start_s=10.0, end_s=20.0, spike_score=2.0),
    ]
    ranked = rank_segments(segments, contexts={99: "pog"}, keywords=["pog"])
    assert ranked == [segments[0], segments[1]]


def test_keyword_bonus_cap_parity_between_clip_and_segment_paths() -> None:
    """Keyword cap behavior matches in clip and segment scoring wrappers."""
    keywords = ["a", "b", "c", "d"]
    text = "a b c d"
    clip = ClipRef(clip_url="https://x/cap", views=0, title=text)
    segment = Segment(start_s=0.0, end_s=5.0, spike_score=0.0)

    clip_score = score_clip(
        clip,
        now=FIXED_NOW,
        keywords=keywords,
        keyword_bonus=10.0,
        keyword_cap=15.0,
    )
    segment_score = score_segment(
        segment,
        context_text=text,
        keywords=keywords,
        keyword_bonus=10.0,
        keyword_cap=15.0,
    )
    assert clip_score == pytest.approx(15.0)
    assert segment_score == pytest.approx(15.0)


def test_keyword_bonus_case_insensitive_parity_between_paths() -> None:
    """Case-insensitive matching is consistent between clip and segment wrappers."""
    text = "LoL insane play"
    clip = ClipRef(clip_url="https://x/case", views=0, title=text)
    segment = Segment(start_s=0.0, end_s=5.0, spike_score=0.0)

    clip_score = score_clip(clip, now=FIXED_NOW, keywords=["lol"])
    segment_score = score_segment(segment, context_text=text, keywords=["lol"])
    assert clip_score == pytest.approx(segment_score)
