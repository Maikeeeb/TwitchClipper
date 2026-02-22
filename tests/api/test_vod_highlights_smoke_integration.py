"""
Test Plan
- Partitions: integration disabled (skip) vs enabled (full run)
- Boundaries: explicit dependency checks, full chat fetch and non-overlap selection
- Failure modes: stage failure, missing artifacts, invalid JSONL chat output

# Covers: TODO-TEST-VOD-SMOKE
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from backend.vod_chat_fetch import TwitchWebChatError, fetch_vod_chat_to_jsonl
from backend.vod_chat_pipeline import chat_file_to_ranked_segments
from backend.vod_cut import cut_segments
from backend.vod_download import download_vod
from backend.vod_montage import compile_vod_montage
from backend.selection import select_non_overlapping_segments_for_duration

DEFAULT_VOD_URL = "https://www.twitch.tv/videos/2699448530"
REQUIRED_CHAT_KEYS = {"vod_id", "offset_s", "created_at", "user_name", "message"}


def _require_live_integration() -> None:
    if os.getenv("RUN_TWITCH_INTEGRATION") != "1":
        pytest.skip("RUN_TWITCH_INTEGRATION=1 required for live VOD smoke test.")


def _require_runtime_dependencies() -> None:
    scripts_dir = Path(sys.executable).parent
    yt_dlp_name = "yt-dlp.exe" if os.name == "nt" else "yt-dlp"
    yt_dlp_from_venv = scripts_dir / yt_dlp_name
    if yt_dlp_from_venv.exists() and shutil.which("yt-dlp") is None:
        os.environ["PATH"] = f"{scripts_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    missing: list[str] = []
    if shutil.which("yt-dlp") is None:
        missing.append("yt-dlp")
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    if missing:
        pytest.skip(f"Missing required runtime dependency(s): {', '.join(missing)}")


def _smoke_output_dir(tmp_path: Path) -> Path:
    """
    Resolve output dir for smoke test artifacts.

    Default behavior uses tmp_path. Set TWITCH_SMOKE_KEEP_OUTPUT=1 to preserve output
    under manual_test_output/smoke_vod_highlights for manual sanity checks.
    """
    if os.getenv("TWITCH_SMOKE_KEEP_OUTPUT") != "1":
        return tmp_path / "vod_smoke_output"

    configured = os.getenv("TWITCH_SMOKE_OUTPUT_DIR", "manual_test_output/smoke_vod_highlights")
    return Path(configured)


def _step(index: int, total: int, label: str, phase: str, details: str = "") -> None:
    message = f"STEP {index}/{total}: {label} ({phase})"
    if details:
        message = f"{message} - {details}"
    print(message, flush=True)


def _ensure_timestamp_s(chat_path: Path) -> int:
    """
    Normalize fetched chat JSONL so ranking loader can consume it.

    Twitch fetch output uses offset_s. Chat import currently expects timestamp_s.
    """
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


def _fetch_chat_with_retries(
    vod_url: str,
    chat_path: Path,
    *,
    retries: int = 2,
) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fetch_vod_chat_to_jsonl(
                vod_url,
                chat_path,
                max_pages=None,
            )
        except TwitchWebChatError as exc:
            last_error = exc
            transient = "service timeout" in str(exc).lower()
            if (not transient) or attempt >= retries:
                raise
            time.sleep(1.5 * (attempt + 1))

    if last_error is not None:
        raise last_error
    raise RuntimeError("chat fetch retries exhausted unexpectedly")


@pytest.mark.integration
def test_vod_highlights_smoke_full_pipeline_live(tmp_path: Path) -> None:
    """Validation: direct full VOD pipeline produces real output artifacts."""
    _require_live_integration()
    _require_runtime_dependencies()

    output_dir = _smoke_output_dir(tmp_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    vod_url = os.getenv("TWITCH_VOD_URL", DEFAULT_VOD_URL)
    quality = os.getenv("TWITCH_SMOKE_QUALITY", "480p")
    min_count = int(os.getenv("TWITCH_SMOKE_MIN_COUNT", "1"))
    bucket_seconds = int(os.getenv("TWITCH_SMOKE_BUCKET_SECONDS", "30"))
    padding_seconds = int(os.getenv("TWITCH_SMOKE_SEGMENT_PADDING_SECONDS", "20"))
    max_segment_seconds = float(os.getenv("TWITCH_SMOKE_MAX_SEGMENT_SECONDS", "120"))
    diversity_windows = int(os.getenv("TWITCH_SMOKE_DIVERSITY_WINDOWS", "8"))
    keywords = ["wow", "insane", "pog", "lol"]
    chat_path = output_dir / "chat.jsonl"
    clips_dir = output_dir / "clips"
    montage_path = output_dir / "montage.mp4"

    _step(1, 5, "Download VOD", "start", f"url={vod_url}, quality={quality}")
    vod_asset = download_vod(vod_url, output_dir=str(output_dir), quality=quality)
    _step(1, 5, "Download VOD", "done", f"vod_path={vod_asset.vod_path}")

    _step(2, 5, "Fetch Chat", "start", "max_pages=None (full chat replay)")
    chat_summary = _fetch_chat_with_retries(
        vod_url,
        chat_path,
        retries=2,
    )
    _step(2, 5, "Fetch Chat", "done", f"messages_written={chat_summary.get('messages_written')}")
    normalized_rows = _ensure_timestamp_s(chat_path)
    _step(2, 5, "Fetch Chat", "normalized", f"timestamp_s_added={normalized_rows}")

    _step(
        3,
        5,
        "Generate Ranked Segments",
        "start",
        (
            f"bucket_seconds={bucket_seconds}, min_count={min_count}, "
            f"padding_seconds={padding_seconds}"
        ),
    )
    segments = chat_file_to_ranked_segments(
        str(chat_path),
        bucket_seconds=bucket_seconds,
        min_count=min_count,
        padding_seconds=padding_seconds,
        keywords=keywords,
    )
    _step(3, 5, "Generate Ranked Segments", "done", f"segments_count={len(segments)}")

    selected_segments = select_non_overlapping_segments_for_duration(
        segments,
        max_segment_seconds=max_segment_seconds,
        diversity_windows=diversity_windows,
    )
    _step(
        4,
        5,
        "Select/Cut Segment Clips",
        "start",
        (
            f"selected_non_overlap={len(selected_segments)}, "
            f"target_window=480-600s, max_segment_seconds={max_segment_seconds}"
        ),
    )
    clip_paths = cut_segments(
        vod_asset.vod_path,
        selected_segments,
        output_dir=str(clips_dir),
    )
    _step(4, 5, "Select/Cut Segment Clips", "done", f"clips_count={len(clip_paths)}")

    _step(5, 5, "Compile Montage", "start", f"output={montage_path}")
    final_montage_path = compile_vod_montage(clip_paths, output_path=str(montage_path))
    _step(5, 5, "Compile Montage", "done", f"montage_path={final_montage_path}")

    result = {
        "vod_path": vod_asset.vod_path,
        "chat_path": str(chat_path),
        "segments_count": len(segments),
        "clips_count": len(clip_paths),
        "montage_path": final_montage_path,
        "clips_dir": str(clips_dir),
        "metadata_path": vod_asset.metadata_path,
    }

    required_result_keys = {
        "vod_path",
        "chat_path",
        "segments_count",
        "clips_count",
        "montage_path",
        "clips_dir",
        "metadata_path",
    }
    assert required_result_keys.issubset(result.keys())

    vod_path = Path(result["vod_path"])
    chat_path = Path(result["chat_path"])
    montage_path = Path(result["montage_path"])
    clips_dir = Path(result["clips_dir"])
    metadata_path = Path(result["metadata_path"])

    # Ensure key artifacts exist and are non-empty.
    assert vod_path.exists() and vod_path.stat().st_size > 0
    assert chat_path.exists() and chat_path.stat().st_size > 0
    assert montage_path.exists() and montage_path.stat().st_size > 0
    assert metadata_path.exists() and metadata_path.stat().st_size > 0
    assert clips_dir.exists()

    clip_files = list(clips_dir.glob("*.mp4"))
    assert len(clip_files) >= 1
    assert result["clips_count"] == len(clip_files)
    assert result["segments_count"] >= result["clips_count"]

    # Selected windows should be non-overlapping to prevent repeated footage.
    ordered_selected = sorted(selected_segments, key=lambda segment: segment.start_s)
    for previous, current in zip(ordered_selected, ordered_selected[1:]):
        assert previous.end_s <= current.start_s
    assert all((segment.end_s - segment.start_s) <= max_segment_seconds for segment in selected_segments)

    # Parse a few chat rows to verify JSONL shape and required keys.
    parsed_rows = 0
    with chat_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            assert REQUIRED_CHAT_KEYS.issubset(row.keys())
            parsed_rows += 1
            if parsed_rows >= 10:
                break
    assert parsed_rows >= 1
