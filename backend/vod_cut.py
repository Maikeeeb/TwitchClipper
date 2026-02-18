"""
VOD segment cutting using ffmpeg.

Cuts ranked segments from a VOD file into individual segment clips.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from backend.vod_models import Segment


def ffmpeg_available() -> bool:
    """
    Check if ffmpeg is available on PATH.

    Returns:
        True if ffmpeg executable is found, False otherwise.
    """
    return shutil.which("ffmpeg") is not None


def cut_segments(
    vod_path: str,
    segments: list[Segment],
    *,
    output_dir: str,
    max_segments: int | None = None,
    min_segment_seconds: float = 1.0,
) -> list[str]:
    """
    Cut ranked segments from a VOD file into individual clips.

    Args:
        vod_path: Path to input VOD mp4 file.
        segments: List of Segment objects (ranked, not mutated).
        output_dir: Directory where segment clips will be written.
        max_segments: If set, only cut first N segments (ranked order).
        min_segment_seconds: Skip segments with duration < this threshold.

    Returns:
        List of output segment file paths in cut order.

    Raises:
        ValueError: If vod_path does not exist or is not .mp4.
        RuntimeError: If ffmpeg is not found on PATH.
    """
    # Validate input
    if not os.path.exists(vod_path):
        raise ValueError(f"vod_path does not exist: {vod_path}")
    if not vod_path.endswith(".mp4"):
        raise ValueError(f"vod_path must end with .mp4: {vod_path}")
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg not found on PATH")

    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Determine which segments to cut
    segments_to_cut = segments
    if max_segments is not None:
        segments_to_cut = segments[:max_segments]

    output_paths: list[str] = []
    for i, segment in enumerate(segments_to_cut):
        # Compute segment duration
        duration = segment.end_s - segment.start_s
        if duration < min_segment_seconds:
            continue

        # Build deterministic output filename
        start_int = int(segment.start_s)
        end_int = int(segment.end_s)
        output_filename = (
            f"segment_{i:03d}_{start_int}_{end_int}.mp4"
        )
        output_path = os.path.join(output_dir, output_filename)

        # Use ffmpeg to cut segment with stream copy (no re-encode)
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-ss", str(segment.start_s),  # Start time
            "-t", str(duration),  # Duration
            "-i", vod_path,  # Input
            "-c", "copy",  # Copy streams without re-encode
            output_path,
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"ffmpeg failed to cut segment {i}: {e.stderr}"
            ) from e

        output_paths.append(output_path)

    return output_paths
