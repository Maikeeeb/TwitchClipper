"""
Test Plan
- Partitions: fill_duration success (real mp4), failure (VideoFileClip raises)
- Boundaries: duration_s > 0, JSON roundtrip includes duration_s
- Failure modes: graceful handling when duration cannot be read (duration_s=None)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.clip_models import ClipAsset, ClipRef, read_clip_metadata, write_clip_metadata
from backend.clips import fill_duration

# Covers: TODO-DUR-001

MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
SAMPLE_MP4 = MEDIA_DIR / "sample_clip_1.mp4"


def _make_asset(output_path: str, duration_s: float | None = None) -> ClipAsset:
    ref = ClipRef(clip_url="https://example.com/clip/1", streamer="x", views=100, title=None)
    return ClipAsset(
        clip_ref=ref,
        mp4_url="https://cdn.example.com/v.mp4",
        output_path=output_path,
        downloaded_at="2025-01-15T12:00:00Z",
        duration_s=duration_s,
        created_at=None,
    )


@pytest.mark.skipif(
    not SAMPLE_MP4.exists(),
    reason="Run python scripts/generate_test_media.py to create tests/media sample mp4s",
)
def test_fill_duration_reads_from_synthetic_mp4() -> None:
    """Reads duration from tests/media synthetic mp4; duration_s is populated and > 0."""
    asset = _make_asset(str(SAMPLE_MP4), duration_s=None)
    result = fill_duration(asset)
    assert result is asset
    assert asset.duration_s is not None
    assert asset.duration_s > 0
    # sample_clip_1.mp4 is 5 seconds
    assert 4.0 <= asset.duration_s <= 6.0


@pytest.mark.skipif(
    not SAMPLE_MP4.exists(),
    reason="Run python scripts/generate_test_media.py to create tests/media sample mp4s",
)
def test_fill_duration_duration_s_positive() -> None:
    """duration_s must be strictly positive for valid mp4."""
    asset = _make_asset(str(SAMPLE_MP4))
    fill_duration(asset)
    assert asset.duration_s is not None
    assert asset.duration_s > 0


def test_duration_s_persisted_in_json_roundtrip(tmp_path: Path) -> None:
    """Write asset with duration_s; read back from sidecar; duration_s present."""
    mp4_path = tmp_path / "clip.mp4"
    mp4_path.write_bytes(b"fake mp4 content")  # file exists but not real video
    asset = _make_asset(str(mp4_path), duration_s=42.5)
    write_clip_metadata(asset)
    json_path = mp4_path.with_suffix(".json")
    assert json_path.exists()
    data = json_path.read_text()
    assert "duration_s" in data
    assert "42.5" in data

    read_asset = read_clip_metadata(json_path)
    assert read_asset.duration_s is not None
    assert abs(read_asset.duration_s - 42.5) < 1e-6


def test_fill_duration_graceful_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When VideoFileClip raises, duration_s is set to None and no crash."""
    mp4_path = tmp_path / "nonexistent.mp4"
    asset = _make_asset(str(mp4_path), duration_s=None)

    def _raise(*_args, **_kwargs):
        raise OSError("cannot read video")

    monkeypatch.setattr("backend.clips.VideoFileClip", _raise)

    result = fill_duration(asset)
    assert result is asset
    assert asset.duration_s is None


def test_fill_duration_graceful_failure_sets_none_even_if_asset_had_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """On read failure, duration_s becomes None (overwrites any prior value)."""
    mp4_path = tmp_path / "bad.mp4"
    asset = _make_asset(str(mp4_path), duration_s=99.0)

    def _raise(*_args, **_kwargs):
        raise RuntimeError("corrupt file")

    monkeypatch.setattr("backend.clips.VideoFileClip", _raise)

    fill_duration(asset)
    assert asset.duration_s is None
