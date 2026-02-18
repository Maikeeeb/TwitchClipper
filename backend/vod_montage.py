"""
VOD montage compilation from segment clips.

Compiles cut segment clips into a final montage MP4 with duration constraints.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
except ImportError:
    VideoFileClip = None


def _get_clip_duration(clip_path: str) -> float | None:
    """
    Get duration of an mp4 clip in seconds.

    Returns:
        Duration in seconds, or None if unable to read.
    """
    if VideoFileClip is None:
        return None

    try:
        clip = VideoFileClip(clip_path)
        try:
            duration = float(clip.duration)
            return duration
        finally:
            clip.close()
    except Exception:
        return None


def compile_vod_montage(
    segment_paths: list[str],
    *,
    output_path: str,
    min_seconds: int = 480,
    max_seconds: int = 600,
) -> str:
    """
    Compile segment clips into a montage within duration constraints.

    Selects clips in input order until total duration is within [min_seconds, max_seconds].
    Never exceeds max_seconds. If unable to reach min_seconds, returns best possible under max.

    Args:
        segment_paths: List of input segment mp4 file paths (ranked order).
        output_path: Path to write final montage mp4.
        min_seconds: Target minimum montage duration (default 480 = 8 minutes).
        max_seconds: Target maximum montage duration (default 600 = 10 minutes).

    Returns:
        Path to output montage file.

    Raises:
        ValueError: If segment_paths is empty or no files exist.
        RuntimeError: If ffmpeg concat fails.
    """
    if not segment_paths:
        raise ValueError("segment_paths must not be empty")

    # Filter to existing files
    existing_paths = [p for p in segment_paths if os.path.exists(p)]
    if not existing_paths:
        raise ValueError("no valid segment files found in segment_paths")

    # Get durations for each clip
    durations: dict[str, float | None] = {}
    for path in existing_paths:
        durations[path] = _get_clip_duration(path)

    # Select clips within duration window (greedy, in order)
    selected_paths: list[str] = []
    total_duration = 0.0
    for path in existing_paths:
        d = durations[path]
        if d is None or d <= 0:
            continue
        if total_duration + d > max_seconds:
            continue
        selected_paths.append(path)
        total_duration += d
        if total_duration >= min_seconds:
            break

    if not selected_paths:
        # Fallback: use first valid clip
        for path in existing_paths:
            d = durations[path]
            if d is not None and d > 0:
                selected_paths = [path]
                break

    if not selected_paths:
        raise ValueError(
            "no valid clips found (all have missing/zero duration)"
        )

    # Write ffmpeg concat list to temp file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as f:
        concat_file = f.name
        for path in selected_paths:
            # Escape quotes and write line
            f.write(f"file '{path}'\n")

    try:
        # Run ffmpeg concat
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",  # Stream copy (no re-encode)
            output_path,
        ]

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffmpeg concat failed: {e.stderr}"
        ) from e
    finally:
        # Clean up temp concat file
        try:
            os.unlink(concat_file)
        except OSError:
            pass

    return output_path
