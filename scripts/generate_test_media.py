"""
Generate deterministic, tiny test video assets for offline testing.

Creates mp4 files under tests/media/ using ffmpeg only. Idempotent:
only generates files that are missing. Run from repo root or any directory.
"""

import os
import shutil
import subprocess
import sys


REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir)
)
MEDIA_DIR = os.path.join(REPO_ROOT, "tests", "media")

# (output basename, duration_sec, ffmpeg -f lavfi -i ..., extra_vf)
# drawtext needs escaping for shell; we pass as list to subprocess so no shell.
VIDEOS = [
    (
        "sample_vod.mp4",
        10,
        ["testsrc=duration=10:size=640x360:rate=30"],
        None,
    ),
    (
        "sample_clip_1.mp4",
        5,
        ["color=c=#333399:s=640x360:d=5:r=30"],
        "drawtext=text='CLIP 1':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
    ),
    (
        "sample_clip_2.mp4",
        5,
        ["color=c=#339933:s=640x360:d=5:r=30"],
        "drawtext=text='CLIP 2':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
    ),
    (
        "sample_clip_3.mp4",
        5,
        ["color=c=#993333:s=640x360:d=5:r=30"],
        "drawtext=text='CLIP 3':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
    ),
]


def ffmpeg_ok() -> bool:
    return shutil.which("ffmpeg") is not None


def run_ffmpeg(args: list[str]) -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
            check=True,
            cwd=REPO_ROOT,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"ffmpeg error: {e}", file=sys.stderr)
        return False


def generate_one(
    out_basename: str,
    duration: int,
    lavfi_input: list[str],
    drawtext_vf: str | None,
) -> bool:
    out_path = os.path.join(MEDIA_DIR, out_basename)
    if os.path.isfile(out_path):
        return True
    os.makedirs(MEDIA_DIR, exist_ok=True)
    # -t to enforce duration; -b:v low to keep <1MB
    common = [
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-b:v",
        "80k",
        "-pix_fmt",
        "yuv420p",
        out_path,
    ]
    if drawtext_vf:
        vf = f"-vf {drawtext_vf}"
        # Build as list: -vf "drawtext=..."
        args = ["-f", "lavfi", "-i", lavfi_input[0], "-vf", drawtext_vf] + common
    else:
        args = ["-f", "lavfi", "-i", lavfi_input[0]] + common
    return run_ffmpeg(args)


def main() -> int:
    if not ffmpeg_ok():
        print("ffmpeg not found. Install ffmpeg and ensure it is on PATH.", file=sys.stderr)
        return 1
    generated = 0
    for out_basename, duration, lavfi_input, drawtext_vf in VIDEOS:
        if not generate_one(out_basename, duration, lavfi_input, drawtext_vf):
            return 1
        out_path = os.path.join(MEDIA_DIR, out_basename)
        if os.path.isfile(out_path):
            generated += 1
    # Print final file sizes
    print("Test media under tests/media/:")
    for out_basename, _, _, _ in VIDEOS:
        path = os.path.join(MEDIA_DIR, out_basename)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            print(f"  {out_basename}: {size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
