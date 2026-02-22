"""
Test Plan
- Partitions: live boundary (1->2) vs local synthetic boundaries (2->3, 3->4, 4->5)
- Boundaries: unlimited chat fetch, small segment windows, short synthetic VOD duration
- Failure modes: missing dependencies, schema mismatch between stages, empty stage output

# Covers: TODO-TEST-VOD-SMOKE
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from backend.vod_chat_fetch import fetch_vod_chat_to_jsonl
from backend.vod_chat_pipeline import chat_file_to_ranked_segments
from backend.vod_cut import cut_segments, ffmpeg_available
from backend.vod_download import download_vod
from backend.vod_models import Segment
from backend.vod_montage import VideoFileClip, compile_vod_montage

DEFAULT_VOD_URL = "https://www.twitch.tv/videos/2699448530"
REQUIRED_CHAT_KEYS = {"vod_id", "offset_s", "created_at", "user_name", "message"}


def _require_live_integration() -> None:
    if os.getenv("RUN_TWITCH_INTEGRATION") != "1":
        pytest.skip("RUN_TWITCH_INTEGRATION=1 required for live Twitch connection test.")


def _ensure_yt_dlp_on_path() -> None:
    scripts_dir = Path(sys.executable).parent
    yt_dlp_name = "yt-dlp.exe" if os.name == "nt" else "yt-dlp"
    yt_dlp_from_venv = scripts_dir / yt_dlp_name
    if yt_dlp_from_venv.exists() and shutil.which("yt-dlp") is None:
        os.environ["PATH"] = f"{scripts_dir}{os.pathsep}{os.environ.get('PATH', '')}"


def _require_download_and_cut_dependencies() -> None:
    _ensure_yt_dlp_on_path()
    missing: list[str] = []
    if shutil.which("yt-dlp") is None:
        missing.append("yt-dlp")
    if not ffmpeg_available():
        missing.append("ffmpeg")
    if missing:
        pytest.skip(f"Missing required runtime dependency(s): {', '.join(missing)}")


def _ensure_timestamp_s(chat_path: Path) -> int:
    normalized_rows = 0
    rows: list[str] = []
    with chat_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "timestamp_s" not in obj and "offset_s" in obj:
                obj["timestamp_s"] = obj["offset_s"]
                normalized_rows += 1
            rows.append(json.dumps(obj, ensure_ascii=False))

    chat_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return normalized_rows


def _write_synthetic_chat_jsonl(chat_path: Path) -> None:
    rows: list[dict[str, object]] = []
    for i in range(20):
        rows.append(
            {
                "vod_id": "synthetic",
                "offset_s": float(i),
                "created_at": "2026-01-01T00:00:00Z",
                "user_name": "quiet",
                "message": "calm",
            }
        )
    for i in range(60):
        rows.append(
            {
                "vod_id": "synthetic",
                "offset_s": 30.0 + (i % 3) * 0.2,
                "created_at": "2026-01-01T00:00:10Z",
                "user_name": f"burst_{i}",
                "message": "wow insane pog",
            }
        )
    chat_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _create_synthetic_vod(vod_path: Path, *, duration_s: int = 20) -> None:
    vod_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=30",
        "-t",
        str(duration_s),
        "-pix_fmt",
        "yuv420p",
        str(vod_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


@pytest.mark.integration
def test_connection_1_to_2_download_to_chat_fetch_live(tmp_path: Path) -> None:
    """Validation: stage 1 output (vod_url/vod) is consumable by stage 2 chat fetch."""
    _require_live_integration()
    _require_download_and_cut_dependencies()

    vod_url = os.getenv("TWITCH_VOD_URL", DEFAULT_VOD_URL)
    quality = os.getenv("TWITCH_SMOKE_QUALITY", "160p")

    output_dir = tmp_path / "connection_1_2"
    chat_path = output_dir / "chat.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)

    vod_asset = download_vod(vod_url, output_dir=str(output_dir), quality=quality)
    assert Path(vod_asset.vod_path).exists()
    assert Path(vod_asset.vod_path).stat().st_size > 0

    summary = fetch_vod_chat_to_jsonl(
        vod_url,
        chat_path,
        max_pages=None,
    )
    assert chat_path.exists()
    assert chat_path.stat().st_size > 0
    assert int(summary["messages_written"]) > 0

    first_line = chat_path.read_text(encoding="utf-8").splitlines()[0]
    first = json.loads(first_line)
    assert REQUIRED_CHAT_KEYS.issubset(first.keys())


def test_connection_2_to_3_chat_to_ranked_segments(tmp_path: Path) -> None:
    """Validation: stage 2 chat JSONL can be normalized and consumed by stage 3 ranking."""
    chat_path = tmp_path / "connection_2_3.chat.jsonl"
    _write_synthetic_chat_jsonl(chat_path)
    normalized_rows = _ensure_timestamp_s(chat_path)

    segments = chat_file_to_ranked_segments(
        str(chat_path),
        bucket_seconds=10,
        min_count=3,
        padding_seconds=6,
        keywords=["wow", "insane", "pog"],
    )

    assert normalized_rows > 0
    assert len(segments) >= 1
    assert segments[0].end_s > segments[0].start_s


@pytest.mark.integration
def test_connection_3_to_4_ranked_segments_to_cut_clips(tmp_path: Path) -> None:
    """Validation: stage 3 ranked segments are consumable by stage 4 clip cutting."""
    if not ffmpeg_available():
        pytest.skip("ffmpeg not available")

    vod_path = tmp_path / "connection_3_4_vod.mp4"
    chat_path = tmp_path / "connection_3_4.chat.jsonl"
    clips_dir = tmp_path / "connection_3_4_clips"

    _create_synthetic_vod(vod_path, duration_s=20)
    _write_synthetic_chat_jsonl(chat_path)
    _ensure_timestamp_s(chat_path)

    segments = chat_file_to_ranked_segments(
        str(chat_path),
        bucket_seconds=10,
        min_count=3,
        padding_seconds=5,
        keywords=["wow", "insane"],
    )
    assert len(segments) >= 1

    clip_paths = cut_segments(
        str(vod_path),
        segments,
        output_dir=str(clips_dir),
        max_segments=2,
    )
    assert len(clip_paths) >= 1
    assert all(Path(path).exists() for path in clip_paths)


@pytest.mark.integration
def test_connection_4_to_5_cut_clips_to_montage(tmp_path: Path) -> None:
    """Validation: stage 4 clip outputs are consumable by stage 5 montage compilation."""
    if not ffmpeg_available():
        pytest.skip("ffmpeg not available")
    if VideoFileClip is None:
        pytest.skip("moviepy is required for real montage duration selection")

    vod_path = tmp_path / "connection_4_5_vod.mp4"
    clips_dir = tmp_path / "connection_4_5_clips"
    montage_path = tmp_path / "connection_4_5_montage.mp4"

    _create_synthetic_vod(vod_path, duration_s=20)
    seed_segments = [
        Segment(start_s=0.0, end_s=4.0, spike_score=2.0),
        Segment(start_s=6.0, end_s=10.0, spike_score=1.5),
    ]

    clip_paths = cut_segments(
        str(vod_path),
        seed_segments,
        output_dir=str(clips_dir),
        max_segments=2,
    )
    assert len(clip_paths) == 2

    final_path = compile_vod_montage(
        clip_paths,
        output_path=str(montage_path),
        min_seconds=1,
        max_seconds=30,
    )
    assert Path(final_path).exists()
    assert Path(final_path).stat().st_size > 0
