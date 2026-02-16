"""
Test Plan
- Partitions: exact fit, early stop at min, skip exceeds max, best under max
- Boundaries: empty list, all duration_s=None
- Failure modes: input not mutated
"""

from pathlib import Path

import pytest

from backend.clip_models import ClipAsset, ClipRef
from backend.selection import (
    MAX_MONTAGE_SECONDS,
    MIN_MONTAGE_SECONDS,
    select_clips_for_duration,
)

# Covers: TODO-SELECT-001


def _make_asset(
    clip_id: str,
    duration_s: float | None,
    streamer: str = "x",
) -> ClipAsset:
    ref = ClipRef(
        clip_url=f"https://example.com/clip/{clip_id}",
        streamer=streamer,
        views=100,
        title=None,
    )
    return ClipAsset(
        clip_ref=ref,
        mp4_url="https://cdn.example.com/v.mp4",
        output_path=f"/tmp/{clip_id}.mp4",
        downloaded_at="2025-01-15T12:00:00Z",
        duration_s=duration_s,
        created_at=None,
    )


def test_exact_fit_within_range() -> None:
    """Exact fit: clips sum to value within [min, max]; all included, stops at min."""
    # 3 * 180 = 540s, in [480, 600]; d would exceed 600, not added
    assets = [
        _make_asset("a", 180.0),
        _make_asset("b", 180.0),
        _make_asset("c", 180.0),
        _make_asset("d", 120.0),
    ]
    result = select_clips_for_duration(
        assets,
        min_seconds=MIN_MONTAGE_SECONDS,
        max_seconds=MAX_MONTAGE_SECONDS,
    )
    assert len(result) == 3
    assert result[0].clip_ref.clip_url.endswith("/clip/a")
    assert result[1].clip_ref.clip_url.endswith("/clip/b")
    assert result[2].clip_ref.clip_url.endswith("/clip/c")
    total = sum(a.duration_s or 0 for a in result)
    assert 480 <= total <= 600


def test_stops_when_hitting_min_seconds() -> None:
    """Stops early once total >= min_seconds; later clips not considered."""
    # First two: 300 + 200 = 500 >= 480
    assets = [
        _make_asset("a", 300.0),
        _make_asset("b", 200.0),
        _make_asset("c", 100.0),
    ]
    result = select_clips_for_duration(
        assets,
        min_seconds=480,
        max_seconds=600,
    )
    assert len(result) == 2
    total = sum(a.duration_s or 0 for a in result)
    assert total == 500
    assert total >= 480


def test_skips_clip_that_would_exceed_max() -> None:
    """Skips clip that would push total over max_seconds; may add later smaller clip."""
    # a=400, b=250 would exceed 600; c=150 fits: 400+150=550
    assets = [
        _make_asset("a", 400.0),
        _make_asset("b", 250.0),
        _make_asset("c", 150.0),
    ]
    result = select_clips_for_duration(
        assets,
        min_seconds=480,
        max_seconds=600,
    )
    assert len(result) == 2
    assert result[0].clip_ref.clip_url.endswith("/clip/a")
    assert result[1].clip_ref.clip_url.endswith("/clip/c")
    total = sum(a.duration_s or 0 for a in result)
    assert total == 550
    assert total <= 600


def test_returns_best_under_max_when_cannot_hit_min() -> None:
    """When unable to reach min_seconds, returns best possible under max."""
    # Only 3 clips of 120s = 360s; min=480 unreachable
    assets = [
        _make_asset("a", 120.0),
        _make_asset("b", 120.0),
        _make_asset("c", 120.0),
    ]
    result = select_clips_for_duration(
        assets,
        min_seconds=480,
        max_seconds=600,
    )
    assert len(result) == 3
    total = sum(a.duration_s or 0 for a in result)
    assert total == 360
    assert total <= 600
    assert total < 480


def test_handles_empty_list() -> None:
    """Empty input returns empty list."""
    result = select_clips_for_duration(
        [],
        min_seconds=480,
        max_seconds=600,
    )
    assert result == []


def test_handles_clips_with_duration_none() -> None:
    """Skips clips where duration_s is None; uses only valid durations."""
    assets = [
        _make_asset("a", None),
        _make_asset("b", 300.0),
        _make_asset("c", None),
        _make_asset("d", 250.0),
    ]
    result = select_clips_for_duration(
        assets,
        min_seconds=480,
        max_seconds=600,
    )
    assert len(result) == 2
    assert result[0].clip_ref.clip_url.endswith("/clip/b")
    assert result[1].clip_ref.clip_url.endswith("/clip/d")
    total = sum(a.duration_s or 0 for a in result)
    assert total == 550


def test_skips_duration_zero_or_negative() -> None:
    """Skips clips with duration_s <= 0."""
    assets = [
        _make_asset("a", 0.0),
        _make_asset("b", -1.0),
        _make_asset("c", 500.0),
    ]
    result = select_clips_for_duration(
        assets,
        min_seconds=480,
        max_seconds=600,
    )
    assert len(result) == 1
    assert result[0].clip_ref.clip_url.endswith("/clip/c")


def test_does_not_mutate_input() -> None:
    """Input list is not mutated."""
    assets = [
        _make_asset("a", 300.0),
        _make_asset("b", 300.0),
    ]
    original = list(assets)
    select_clips_for_duration(assets, min_seconds=480, max_seconds=600)
    assert assets == original
    assert len(assets) == 2


def test_default_constants() -> None:
    """MIN and MAX constants are 8 and 10 minutes."""
    assert MIN_MONTAGE_SECONDS == 8 * 60
    assert MAX_MONTAGE_SECONDS == 10 * 60


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "media" / "sample_clip_1.mp4").exists(),
    reason="Run python scripts/generate_test_media.py",
)
def test_integration_total_duration_in_window() -> None:
    """Optional: Build ClipAssets from tests/media; total falls in 8–10 min window."""
    media_dir = Path(__file__).resolve().parent.parent / "media"
    # sample_clip_1/2/3 are ~5s each; sample_vod is ~10s
    files = [
        ("sample_clip_1.mp4", 5.0),
        ("sample_clip_2.mp4", 5.0),
        ("sample_clip_3.mp4", 5.0),
        ("sample_vod.mp4", 10.0),
    ]
    assets = []
    for i, (fname, dur) in enumerate(files):
        path = media_dir / fname
        if not path.exists():
            pytest.skip(f"Missing {path}")
        ref = ClipRef(
            clip_url=f"https://example.com/{fname}",
            streamer="test",
            views=100,
            title=None,
        )
        assets.append(
            ClipAsset(
                clip_ref=ref,
                mp4_url=f"file://{path}",
                output_path=str(path),
                downloaded_at="2025-01-15T12:00:00Z",
                duration_s=dur,
                created_at=None,
            )
        )
    # Total 25s; use small window to verify behavior
    result = select_clips_for_duration(
        assets,
        min_seconds=20,
        max_seconds=30,
    )
    total = sum(a.duration_s or 0 for a in result)
    assert 20 <= total <= 30
    assert len(result) >= 4
