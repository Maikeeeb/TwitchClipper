"""
Test Plan
- Partitions: dedupe by identity, max_per_streamer, missing streamer/views/title
- Boundaries: empty list, exact dupes, query-param dupes, tie-break
- Defect: input list not mutated
"""

import pytest

from backend.clip_models import ClipRef
from backend.filtering import clip_identity, filter_clips, normalize_clip_url


# ---- URL helpers ----


def test_normalize_clip_url_removes_query_params() -> None:
    """Query params are removed."""
    url = "https://www.twitch.tv/x/clip/Abc123?t=0&foo=bar"
    assert normalize_clip_url(url) == "https://www.twitch.tv/x/clip/Abc123"


def test_normalize_clip_url_removes_trailing_slash() -> None:
    """Trailing slash is removed."""
    url = "https://www.twitch.tv/x/clip/Abc123/"
    assert normalize_clip_url(url) == "https://www.twitch.tv/x/clip/Abc123"


def test_normalize_clip_url_both() -> None:
    """Query and trailing slash both removed."""
    url = "https://www.twitch.tv/x/clip/Abc123/?t=0"
    assert normalize_clip_url(url) == "https://www.twitch.tv/x/clip/Abc123"


def test_clip_identity_uses_last_segment_after_clip() -> None:
    """Identity is last path segment after /clip/ when present."""
    url = "https://www.twitch.tv/user/clip/AbcDef123"
    assert clip_identity(url) == "AbcDef123"


def test_clip_identity_fallback_normalized_url() -> None:
    """When no /clip/, identity is normalized URL."""
    url = "https://www.twitch.tv/some/path"
    assert clip_identity(url) == "https://www.twitch.tv/some/path"


def test_clip_identity_same_for_query_params() -> None:
    """URLs differing only by query params get same identity."""
    a = "https://www.twitch.tv/x/clip/Slug?t=0"
    b = "https://www.twitch.tv/x/clip/Slug?t=10"
    assert clip_identity(a) == clip_identity(b) == "Slug"


# ---- filter_clips ----


def test_filter_clips_exact_duplicate_urls_removed() -> None:
    """Exact duplicate URLs are deduplicated."""
    ref = ClipRef(clip_url="https://twitch.tv/x/clip/Abc", views=100)
    clips = [ref, ref]
    result = filter_clips(clips)
    assert len(result) == 1
    assert result[0].clip_url == ref.clip_url


def test_filter_clips_query_params_treated_as_duplicate() -> None:
    """URLs differing only by query params are treated as duplicates."""
    a = ClipRef(clip_url="https://twitch.tv/x/clip/Slug", views=100)
    b = ClipRef(clip_url="https://twitch.tv/x/clip/Slug?t=0", views=100)
    result = filter_clips([a, b])
    assert len(result) == 1


def test_filter_clips_keeps_higher_views_when_duplicates() -> None:
    """When duplicates exist, keep the clip with higher views (None -> 0)."""
    low = ClipRef(clip_url="https://twitch.tv/x/clip/Slug", views=10)
    high = ClipRef(clip_url="https://twitch.tv/x/clip/Slug?x=1", views=500)
    result = filter_clips([low, high])
    assert len(result) == 1
    assert result[0].views == 500


def test_filter_clips_keeps_higher_views_none_treated_as_zero() -> None:
    """Duplicate with views beats duplicate with None views."""
    no_views = ClipRef(clip_url="https://twitch.tv/x/clip/Slug", views=None)
    with_views = ClipRef(clip_url="https://twitch.tv/x/clip/Slug/", views=1)
    result = filter_clips([no_views, with_views])
    assert len(result) == 1
    assert result[0].views == 1


def test_filter_clips_stable_order_preserved() -> None:
    """First occurrence determines position; best clip (by views) is kept at that position."""
    # Identity A first with low views, then B, then A again with high views
    a_low = ClipRef(clip_url="https://twitch.tv/x/clip/A", views=10)
    b_ref = ClipRef(clip_url="https://twitch.tv/y/clip/B", views=100)
    a_high = ClipRef(clip_url="https://twitch.tv/x/clip/A?q=1", views=500)
    result = filter_clips([a_low, b_ref, a_high])
    assert len(result) == 2
    # Order: A (first occurrence), then B. A should be the high-views one.
    assert result[0].views == 500
    assert result[1].views == 100


def test_filter_clips_max_per_streamer() -> None:
    """max_per_streamer caps clips per streamer; prefers higher views."""
    clips = [
        ClipRef(clip_url="https://x/clip/1", streamer="alice", views=100),
        ClipRef(clip_url="https://x/clip/2", streamer="alice", views=500),
        ClipRef(clip_url="https://x/clip/3", streamer="alice", views=200),
        ClipRef(clip_url="https://x/clip/4", streamer="bob", views=50),
    ]
    result = filter_clips(clips, max_per_streamer=2)
    assert len(result) == 3  # 2 alice + 1 bob
    alice_views = [r.views for r in result if r.streamer == "alice"]
    assert alice_views == [500, 200]  # top 2 by views


def test_filter_clips_max_per_streamer_tie_break_clip_url() -> None:
    """Within streamer, tie-break by clip_url."""
    clips = [
        ClipRef(clip_url="https://x/clip/bbb", streamer="x", views=100),
        ClipRef(clip_url="https://x/clip/aaa", streamer="x", views=100),
    ]
    result = filter_clips(clips, max_per_streamer=1)
    assert len(result) == 1
    assert result[0].clip_url == "https://x/clip/aaa"  # lex order


def test_filter_clips_handles_missing_streamer_views_title() -> None:
    """Missing streamer (""), views, title do not crash."""
    clips = [
        ClipRef(clip_url="https://x/clip/a", streamer="", views=None, title=None),
        ClipRef(clip_url="https://x/clip/b", streamer="", views=10, title=None),
    ]
    result = filter_clips(clips, max_per_streamer=1)
    assert len(result) == 1
    assert result[0].views == 10


def test_filter_clips_does_not_mutate_input() -> None:
    """Input list is not mutated."""
    a = ClipRef(clip_url="https://x/clip/a", views=100)
    b = ClipRef(clip_url="https://x/clip/b", views=200)
    original = [a, b]
    original_len = len(original)
    result = filter_clips(original)
    assert len(original) == original_len
    assert original[0] is a
    assert original[1] is b


def test_filter_clips_empty_list() -> None:
    """Empty list returns empty list."""
    assert filter_clips([]) == []
    assert filter_clips([], max_per_streamer=2) == []
