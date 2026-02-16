"""
Test Plan
- Partitions: parse_views (K, M, plain), ClipRef/ClipAsset creation, JSON round-trip
- Boundaries: empty string, missing title/views, None values
- Failure modes: invalid parse_views input
"""

import json
from pathlib import Path

import pytest

from backend.clip_models import (
    ClipAsset,
    ClipRef,
    parse_views,
    read_clip_metadata,
    write_clip_metadata,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.2K", 1200),
        ("45", 45),
        ("", None),
        ("  100  ", 100),
        ("2.5M", 2500000),
        ("1K", 1000),
        ("1M", 1_000_000),
        ("0", 0),
    ],
)
def test_parse_views(text: str, expected: int | None) -> None:
    """Unit test: parse_views handles K, M, plain numbers, empty."""
    assert parse_views(text) == expected


def test_parse_views_invalid_returns_none() -> None:
    """Defect: invalid input returns None without raising."""
    assert parse_views("abc") is None
    assert parse_views("1.2.3") is None


def test_clip_ref_creation_missing_title_views() -> None:
    """Boundary: ClipRef with missing optional title and views."""
    ref = ClipRef(clip_url="https://twitch.tv/x/clip/y", streamer="x")
    assert ref.views is None
    assert ref.title is None
    assert ref.clip_url == "https://twitch.tv/x/clip/y"


def test_clip_ref_from_url() -> None:
    """Adapter: ClipRef.from_url creates ref from string."""
    ref = ClipRef.from_url("https://example.com/clip/123")
    assert ref.clip_url == "https://example.com/clip/123"
    assert ref.streamer == ""


def test_clip_asset_serialization_roundtrip(tmp_path: Path) -> None:
    """JSON sidecar write creates expected keys and can be read back."""
    ref = ClipRef(
        clip_url="https://twitch.tv/s/clip/abc",
        streamer="s",
        views=1200,
        title="Epic clip",
    )
    asset = ClipAsset(
        clip_ref=ref,
        mp4_url="https://cdn.example.com/video.mp4",
        output_path=str(tmp_path / "clip.mp4"),
        downloaded_at="2025-01-15T12:00:00+00:00",
        duration_s=60.5,
        created_at=None,
    )
    json_path = write_clip_metadata(asset)
    assert json_path.exists()
    assert json_path.suffix == ".json"
    data = json.loads(json_path.read_text())
    assert data.get("schema_version") == 1
    assert "streamer" in data
    assert "clip_url" in data
    assert "mp4_url" in data
    assert "views" in data
    assert "title" in data
    assert "downloaded_at" in data
    assert "duration_s" in data
    assert "created_at" in data
    assert data["views"] == 1200
    assert data["title"] == "Epic clip"
    assert abs((data["duration_s"] or 0) - 60.5) < 1e-6

    read_asset = read_clip_metadata(json_path)
    assert read_asset.clip_ref.clip_url == asset.clip_ref.clip_url
    assert read_asset.clip_ref.views == asset.clip_ref.views
    assert read_asset.mp4_url == asset.mp4_url


def test_read_clip_metadata_from_mp4_path(tmp_path: Path) -> None:
    """read_clip_metadata accepts .mp4 path and finds .json."""
    json_path = tmp_path / "clip.json"
    json_path.write_text(
        json.dumps(
            {
                "clip_url": "https://x",
                "mp4_url": "https://y",
                "downloaded_at": "2025-01-15T12:00:00Z",
                "output_path": str(tmp_path / "clip.mp4"),
            }
        )
    )
    asset = read_clip_metadata(tmp_path / "clip.mp4")
    assert asset.clip_ref.clip_url == "https://x"


def test_read_clip_metadata_without_schema_version(tmp_path: Path) -> None:
    """Old JSON without schema_version still reads (backward compat)."""
    json_path = tmp_path / "clip.json"
    json_path.write_text(
        json.dumps(
            {
                "clip_url": "https://old",
                "mp4_url": "https://cdn/old.mp4",
                "downloaded_at": "2024-01-01T00:00:00Z",
                "output_path": str(tmp_path / "clip.mp4"),
            }
        )
    )
    asset = read_clip_metadata(json_path)
    assert asset.clip_ref.clip_url == "https://old"
