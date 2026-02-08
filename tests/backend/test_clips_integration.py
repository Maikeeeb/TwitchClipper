"""
Test Plan
- Partitions: integration enabled vs stubbed paths
- Boundaries: environment-gated execution
- Failure modes: skip when external integration not enabled
"""

import os
import sys
from pathlib import Path

import pytest

from backend.clips import download_clip, getclips


def test_getclips_integration(monkeypatch, tmp_path: Path) -> None:
    # Covers: TODO-TEST-CLIPS-GETCLIPS
    if os.getenv("RUN_TWITCH_INTEGRATION") == "1":
        monkeypatch.setenv("HEADLESS", "1")
        streamer = os.getenv("TWITCH_STREAMER", "zubatlel")
        clip_links = getclips(
            streamer,
            current_videos_dir=str(tmp_path),
            max_clips=1,
            wait_seconds=30,
            apply_overlay=False,
        )
    else:
        def _fake_getclips(*_args, **kwargs):
            streamer = kwargs.get("name") or kwargs.get("streamer") or _args[0]
            current_videos_dir = kwargs.get("current_videos_dir") or _args[1]
            Path(current_videos_dir, f"{streamer}.mp4").write_text("stubbed")
            return [f"https://www.twitch.tv/{streamer}/clip/stub"]

        monkeypatch.setattr(sys.modules[__name__], "getclips", _fake_getclips)
        streamer = os.getenv("TWITCH_STREAMER", "zubatlel")
        clip_links = getclips(
            streamer,
            current_videos_dir=str(tmp_path),
            max_clips=1,
            wait_seconds=1,
            apply_overlay=False,
        )

    assert clip_links, "Expected at least one clip link."
    if os.getenv("RUN_TWITCH_INTEGRATION") != "1":
        assert clip_links == [f"https://www.twitch.tv/{streamer}/clip/stub"]
        assert (tmp_path / f"{streamer}.mp4").exists()


def test_download_clip_integration(tmp_path: Path) -> None:
    # Covers: TODO-TEST-CLIPS-DOWNLOAD
    if os.getenv("RUN_TWITCH_INTEGRATION") != "1":
        pytest.skip("RUN_TWITCH_INTEGRATION=1 required for live Twitch download.")
    clip_url = os.getenv(
        "TWITCH_CLIP_URL",
        "https://www.twitch.tv/zubatlel/clip/"
        "TawdryTenuousTroutSwiftRage-Z4cHL3l1709hBRep",
    )
    output_path, video_url = download_clip(clip_url, output_dir=str(tmp_path), headless=True)

    assert video_url and ".mp4" in video_url
    output_file = Path(output_path)
    assert output_file.exists()
    assert output_file.stat().st_size > 0
