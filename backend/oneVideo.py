import os
import logging
from pathlib import Path

from moviepy.video.compositing.CompositeVideoClip import (
    CompositeVideoClip,
    concatenate_videoclips,
)
from moviepy.video.fx.SlideIn import SlideIn
from moviepy.video.io.VideoFileClip import VideoFileClip
from natsort import natsorted

from backend.clip_models import read_clip_metadata

logger = logging.getLogger(__name__)


def _extract_streamer_name(filename):
    """Remove digits and extension to recover streamer name from clip filename."""
    return "".join(ch for ch in filename.strip(".mp4") if not ch.isdigit())


def _resolve_streamer_metadata(file_path: str, filename: str) -> tuple[str, str]:
    """
    Resolve streamer display name and source link for a clip.

    Prefers JSON sidecar metadata and falls back to legacy filename parsing.
    """
    fallback_name = _extract_streamer_name(filename)
    fallback_link = f"https://www.twitch.tv/{fallback_name}"
    try:
        asset = read_clip_metadata(Path(file_path))
    except Exception:
        return fallback_name, fallback_link

    streamer_name = (asset.clip_ref.streamer or "").strip() or fallback_name
    clip_url = (asset.clip_ref.clip_url or "").strip()
    if clip_url:
        return streamer_name, clip_url
    return streamer_name, f"https://www.twitch.tv/{streamer_name}"


def compile(
    name,
    current_videos_dir=None,
    full_videos_dir=None,
    time_stamps_path=None,
    streamer_links_path=None,
    max_length_seconds=481,
    target_resolution=(1080, 1920),
):
    """Compile clips from currentVideos into a single highlight video."""
    base_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(base_dir, os.pardir))
    current_videos_dir = current_videos_dir or os.path.join(repo_root, "currentVideos")
    full_videos_dir = full_videos_dir or os.path.join(repo_root, "fullVideos")
    os.makedirs(current_videos_dir, exist_ok=True)
    os.makedirs(full_videos_dir, exist_ok=True)

    L = []
    loaded_videos = []
    current_video_length = 0
    report = {
        "skipped_clips": [],
        "compiled_clips": 0,
        "output_path": None,
    }
    # These metadata files default to the backend folder unless overridden.
    time_stamps_path = time_stamps_path or os.path.join(base_dir, "time stamps")
    streamer_links_path = streamer_links_path or os.path.join(base_dir, "streamer links")
    streamers = []
    with open(time_stamps_path, "w") as time_stamps_file, open(
        streamer_links_path, "w"
    ) as streamer_links_file:
        for root, _, files in os.walk(current_videos_dir):
            files = natsorted(files)
            files.reverse()
            for file in files:
                if os.path.splitext(file)[1] == ".mp4":
                    file_path = os.path.join(root, file)
                    try:
                        video = VideoFileClip(file_path, target_resolution=target_resolution)
                    except Exception as exc:
                        logger.warning(
                            "Skipping unreadable clip during compile",
                            extra={"file_path": file_path, "error": str(exc)},
                        )
                        report["skipped_clips"].append(
                            {
                                "file_path": file_path,
                                "reason": str(exc),
                            }
                        )
                        continue
                    loaded_videos.append(video)
                    L.append(
                        video.with_start(current_video_length - files.index(file)).with_effects(
                            [SlideIn(1, "bottom")]
                        )
                    )
                    # time stamp handler
                    current_video_length = int(current_video_length)
                    timestamp = f"{current_video_length // 60}:{current_video_length % 60:02d}"
                    streamer_name, streamer_link = _resolve_streamer_metadata(file_path, file)
                    time_stamps_file.write(f"{timestamp} - {streamer_name}\n")
                    current_video_length += video.duration - 2
                    # streamer link handler
                    if streamer_name not in streamers:
                        streamer_links_file.write(f"{streamer_name}: {streamer_link}\n")
                        streamers.append(streamer_name)
                    if current_video_length >= max_length_seconds:
                        break
    if not L:
        logger.error(
            "Compile aborted: no valid clips found",
            extra={"current_videos_dir": current_videos_dir, "skipped_count": len(report["skipped_clips"])},
        )
        raise ValueError("No valid clips found to compile.")
    final_clip = [CompositeVideoClip(L)]
    output_path = os.path.join(full_videos_dir, "%s.mp4" % name)
    concatenate_videoclips(final_clip, padding=-1).write_videofile(
        output_path,
        fps=60,
        remove_temp=True,
        threads=12,
    )
    report["compiled_clips"] = len(L)
    report["output_path"] = output_path
    logger.info(
        "Compile completed",
        extra={
            "output_path": output_path,
            "compiled_clips": report["compiled_clips"],
            "skipped_clips": len(report["skipped_clips"]),
        },
    )
    for video in loaded_videos:
        close_video = getattr(video, "close", None)
        if callable(close_video):
            close_video()
    return report


if __name__ == "__main__":
    from datetime import date

    """testing = ImageClip("test.png").set_duration(3)
    testing.write_videofile("testing.mp4",
                            fps=60, remove_temp=True, threads=8)"""

    compile("video1" + str(date.today()))
