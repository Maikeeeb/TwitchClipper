"""
Test Plan
- Partitions: normal ClipRef, missing views/title, boundary values
- Boundaries: views=0, title=None, keyword cap
- Ordering: higher views => higher score (all else equal)
"""

from datetime import datetime, timezone

import pytest

from backend.clip_models import ClipRef
from backend.scoring import rank_clips, score_clip

# Fixed now for deterministic tests
FIXED_NOW = datetime(2025, 2, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_score_clip_higher_views_scores_higher() -> None:
    """Ordering: clip with more views scores strictly higher (all else equal). Covers: TODO-RANK-001."""
    low = ClipRef(clip_url="https://x/clip/a", streamer="x", views=100, title=None)
    high = ClipRef(clip_url="https://x/clip/b", streamer="x", views=5000, title=None)
    assert score_clip(high, now=FIXED_NOW) > score_clip(low, now=FIXED_NOW)


def test_score_clip_negative_views_treated_as_zero() -> None:
    """Defect: negative views must not crash; treated as 0."""
    ref = ClipRef(clip_url="https://x/a", streamer="x", views=-100, title=None)
    s = score_clip(ref, now=FIXED_NOW)
    assert s >= 0
    assert abs(s) < 1e-9  # same as views=0


def test_score_clip_missing_views_treated_as_zero() -> None:
    """Missing views must not crash; treated as 0."""
    ref = ClipRef(clip_url="https://x/clip/a", streamer="x", views=None, title="Epic")
    s = score_clip(ref, now=FIXED_NOW)
    assert s >= 0
    assert isinstance(s, float)
    # With no keywords, score = log1p(0) = 0
    assert abs(s) < 1e-9


def test_score_clip_keyword_bonus_increases_score() -> None:
    """Keyword bonus increases score when title matches."""
    without = ClipRef(clip_url="https://x/a", views=100, title="Some clip")
    with_kw = ClipRef(clip_url="https://x/b", views=100, title="Epic play moment")
    s_without = score_clip(without, now=FIXED_NOW, keywords=["epic"])
    s_with = score_clip(with_kw, now=FIXED_NOW, keywords=["epic"])
    assert s_with > s_without


def test_score_clip_keyword_bonus_capped() -> None:
    """Keyword bonus is capped; many matches don't exceed cap."""
    ref = ClipRef(clip_url="https://x/a", views=100, title="epic epic epic epic epic")
    s = score_clip(
        ref, now=FIXED_NOW, keywords=["epic"], keyword_bonus=10.0, keyword_cap=15.0
    )
    # 5 matches * 10 = 50 raw, capped to 15
    base = score_clip(ref, now=FIXED_NOW)
    bonus_portion = s - base
    assert bonus_portion <= 15.0
    assert bonus_portion > 0


def test_score_clip_boundary_views_zero_title_none() -> None:
    """Boundary: views=0 and title=None yields minimal score, no crash."""
    ref = ClipRef(clip_url="https://x/a", views=0, title=None)
    s = score_clip(ref, now=FIXED_NOW)
    assert abs(s) < 1e-9


def test_score_clip_missing_title_no_crash() -> None:
    """Missing title must not crash; no keyword bonus."""
    ref = ClipRef(clip_url="https://x/a", views=1000, title=None)
    s = score_clip(ref, now=FIXED_NOW, keywords=["epic"])
    assert s > 0
    assert s == score_clip(ref, now=FIXED_NOW)  # same as no keywords


def test_score_clip_deterministic_fixed_now() -> None:
    """Same input and fixed now yield same score."""
    ref = ClipRef(clip_url="https://x/a", views=1234, title="cool")
    a = score_clip(ref, now=FIXED_NOW)
    b = score_clip(ref, now=FIXED_NOW)
    assert a == b


def test_score_clip_normal_input_positive() -> None:
    """Typical ClipRef produces positive score."""
    ref = ClipRef(
        clip_url="https://x/clip/abc",
        streamer="x",
        views=5000,
        title="Epic play highlight",
    )
    s = score_clip(ref, now=FIXED_NOW)
    assert s > 0
    assert isinstance(s, float)


# ---- rank_clips tests (TODO-RANK-002) ----


def test_rank_clips_returns_sorted_by_score() -> None:
    """Returns clips sorted by score, highest first."""
    low = ClipRef(clip_url="https://x/a", views=10, title=None)
    mid = ClipRef(clip_url="https://x/b", views=500, title=None)
    high = ClipRef(clip_url="https://x/c", views=5000, title=None)
    clips = [mid, low, high]
    result = rank_clips(clips, now=FIXED_NOW)
    assert [r.clip_url for r in result] == [
        "https://x/c",
        "https://x/b",
        "https://x/a",
    ]


def test_rank_clips_tie_break_same_score_url_order() -> None:
    """Same score (same views): tie break by clip_url."""
    a = ClipRef(clip_url="https://x/aaa", views=100, title=None)
    b = ClipRef(clip_url="https://x/bbb", views=100, title=None)
    result = rank_clips([b, a], now=FIXED_NOW)
    assert [r.clip_url for r in result] == ["https://x/aaa", "https://x/bbb"]


def test_rank_clips_tie_break_higher_views_first() -> None:
    """Same score, different views: higher views first."""
    # log1p(100)+2.28 ≈ log1p(1000) ≈ 6.9; keyword_bonus=2.28 creates tie
    low_views = ClipRef(clip_url="https://x/low", views=100, title="epic")
    high_views = ClipRef(clip_url="https://x/high", views=1000, title=None)
    result = rank_clips(
        [low_views, high_views],
        now=FIXED_NOW,
        keywords=["epic"],
        keyword_bonus=2.28,
        keyword_cap=15.0,
    )
    assert result[0].views == 1000
    assert result[1].views == 100


def test_rank_clips_does_not_mutate_input() -> None:
    """Input list is not mutated."""
    a = ClipRef(clip_url="https://x/a", views=100, title=None)
    b = ClipRef(clip_url="https://x/b", views=500, title=None)
    original = [a, b]
    original_ids = [id(c) for c in original]
    result = rank_clips(original, now=FIXED_NOW)
    assert result != original  # different list object
    assert original == [a, b]  # order unchanged
    assert [id(c) for c in original] == original_ids  # same refs


def test_rank_clips_empty_list() -> None:
    """Handles empty list."""
    assert rank_clips([], now=FIXED_NOW) == []


def test_rank_clips_missing_views_title_safe() -> None:
    """Handles missing views and title without crashing."""
    refs = [
        ClipRef(clip_url="https://x/a", views=None, title=None),
        ClipRef(clip_url="https://x/b", views=100, title=None),
        ClipRef(clip_url="https://x/c", views=500, title="epic"),
    ]
    result = rank_clips(refs, now=FIXED_NOW, keywords=["epic"])
    assert len(result) == 3
    # c has highest (views + keyword), b middle, a lowest
    assert result[0].clip_url == "https://x/c"
    assert result[2].clip_url == "https://x/a"
