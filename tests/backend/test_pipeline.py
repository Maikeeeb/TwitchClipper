"""
Test Plan
- Partitions: filter before rank, top N, empty list, mutation
- All tests offline: mock getclips and download_clip
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.clip_models import ClipAsset, ClipRef
from backend.pipeline import (
    DEFAULT_MAX_CLIPS,
    PER_STREAMER_K,
    SCRAPE_POOL_SIZE,
    scrape_filter_rank_download,
)


def _make_ref(url: str, views: int | None = None, streamer: str = "x") -> ClipRef:
    return ClipRef(clip_url=url, streamer=streamer, views=views, title=None)


def _make_asset(ref: ClipRef, duration_s: float = 60.0) -> ClipAsset:
    """Assets need duration_s for duration-based selection (8–10 min target)."""
    return ClipAsset(
        clip_ref=ref,
        mp4_url="https://cdn.example.com/v.mp4",
        output_path="/tmp/out.mp4",
        downloaded_at="2025-01-01T00:00:00Z",
        duration_s=duration_s,
        created_at=None,
    )


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_only_top_n_passed_to_download(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """Only top N clips are passed to download_clip. Covers: TODO-RANK-004."""
    refs = [_make_ref(f"https://x/clip/{i}", views=100 - i) for i in range(30)]
    mock_getclips.return_value = refs
    mock_download.side_effect = lambda r, **_: _make_asset(r)

    scrape_filter_rank_download(
        ["alice"],
        str(tmp_path),
        max_clips=5,
        scrape_pool_size=30,
    )

    assert mock_download.call_count == 5
    # Highest views first: 100, 99, 98, 97, 96
    downloaded_views = [c[0][0].views for c in mock_download.call_args_list]
    assert downloaded_views == [100, 99, 98, 97, 96]


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_filter_applied_before_ranking(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """filter_clips is applied; duplicates are removed before ranking."""
    # Same identity (Slug), different query params; different identity (Other)
    dup1 = _make_ref("https://x/clip/Slug", views=10)
    dup2 = _make_ref("https://x/clip/Slug?t=0", views=500)  # higher views kept
    other = _make_ref("https://x/clip/Other", views=100)
    mock_getclips.return_value = [dup1, dup2, other]
    mock_download.side_effect = lambda r, **_: _make_asset(r)

    scrape_filter_rank_download(
        ["alice"],
        str(tmp_path),
        max_clips=10,
        scrape_pool_size=10,
    )

    # After dedupe: 2 refs (Slug with 500 views, Other with 100). Both downloaded.
    assert mock_download.call_count == 2
    urls = {c[0][0].clip_url for c in mock_download.call_args_list}
    assert "https://x/clip/Slug?t=0" in urls or "https://x/clip/Slug" in urls
    assert "https://x/clip/Other" in urls


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_ranking_order_determines_download_order(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """Download order follows rank (highest score first)."""
    low = _make_ref("https://x/clip/low", views=10)
    high = _make_ref("https://x/clip/high", views=5000)
    mock_getclips.return_value = [low, high]
    mock_download.side_effect = lambda r, **_: _make_asset(r)

    scrape_filter_rank_download(["alice"], str(tmp_path), max_clips=2)

    call_order = [c[0][0].clip_url for c in mock_download.call_args_list]
    assert call_order[0] == "https://x/clip/high"
    assert call_order[1] == "https://x/clip/low"


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_empty_list_no_downloads(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """Empty streamer list or no clips: no downloads."""
    mock_getclips.return_value = []

    scrape_filter_rank_download([], str(tmp_path))
    assert mock_download.call_count == 0

    scrape_filter_rank_download(["alice"], str(tmp_path))
    assert mock_download.call_count == 0


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_does_not_mutate_input(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """streamer_names input is not mutated."""
    mock_getclips.return_value = [_make_ref("https://x/clip/a", views=100)]
    mock_download.side_effect = lambda r, **_: _make_asset(r)

    streamers = ["alice", "bob"]
    original = list(streamers)
    scrape_filter_rank_download(streamers, str(tmp_path))

    assert streamers == original


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_handles_missing_views_title(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """Missing views/title do not crash pipeline."""
    ref = ClipRef(clip_url="https://x/clip/a", streamer="x", views=None, title=None)
    mock_getclips.return_value = [ref]
    mock_download.side_effect = lambda r, **_: _make_asset(r)

    result = scrape_filter_rank_download(["alice"], str(tmp_path), max_clips=5)
    assert len(result) == 1


# ---- TODO-RANK-006 multi-streamer tests ----


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_per_streamer_k_limits_candidates_before_global_rank(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """Multi-streamer: only K per streamer considered before global rank. Covers: TODO-RANK-006."""
    # Each streamer returns 15 clips; per_streamer_k=5 means we keep 5 each (10 total) before global rank
    def _getclips_side_effect(name, **kwargs):
        return [
            _make_ref(f"https://{name}/clip/{i}", views=100 - i, streamer=name)
            for i in range(15)
        ]

    mock_getclips.side_effect = _getclips_side_effect
    mock_download.side_effect = lambda r, **_: _make_asset(r)

    scrape_filter_rank_download(
        ["alice", "bob"],
        str(tmp_path),
        max_clips=4,
        scrape_pool_size=15,
        per_streamer_k=5,
    )

    # Global rank picks top 4 from the 10 candidates (5 alice + 5 bob)
    assert mock_download.call_count == 4
    # getclips called once per streamer
    assert mock_getclips.call_count == 2


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_global_ranking_still_controls_final_downloads(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """Downloads follow global rank order, not streamer order."""
    def _getclips_side_effect(name, **kwargs):
        if name == "alice":
            return [_make_ref("https://alice/clip/alice1", views=100, streamer="alice")]
        return [_make_ref("https://bob/clip/bob1", views=5000, streamer="bob")]

    mock_getclips.side_effect = _getclips_side_effect
    mock_download.side_effect = lambda r, **_: _make_asset(r)

    scrape_filter_rank_download(
        ["alice", "bob"],
        str(tmp_path),
        max_clips=2,
        per_streamer_k=5,
    )

    # Bob's clip (5000 views) ranks higher than Alice's (100); bob first
    call_order = [c[0][0].streamer for c in mock_download.call_args_list]
    assert call_order[0] == "bob"
    assert call_order[1] == "alice"


@patch("backend.pipeline.overlay")
@patch("backend.pipeline.download_clip")
@patch("backend.pipeline.getclips")
def test_single_streamer_path_unchanged(
    mock_getclips: MagicMock,
    mock_download: MagicMock,
    mock_overlay: MagicMock,
    tmp_path: Path,
) -> None:
    """Single streamer: same behavior as before (top max_clips from ranked list)."""
    refs = [_make_ref(f"https://x/clip/{i}", views=100 - i, streamer="alice") for i in range(25)]
    mock_getclips.return_value = refs
    mock_download.side_effect = lambda r, **_: _make_asset(r)

    scrape_filter_rank_download(
        ["alice"],
        str(tmp_path),
        max_clips=5,
        scrape_pool_size=25,
    )

    # Still gets top 5 by score (views)
    assert mock_download.call_count == 5
    downloaded_views = [c[0][0].views for c in mock_download.call_args_list]
    assert downloaded_views == [100, 99, 98, 97, 96]
