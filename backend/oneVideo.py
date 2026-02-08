import os

from moviepy.video.compositing.CompositeVideoClip import (
    CompositeVideoClip,
    concatenate_videoclips,
)
from moviepy.video.fx.SlideIn import SlideIn
from moviepy.video.io.VideoFileClip import VideoFileClip
from natsort import natsorted


def _extract_streamer_name(filename):
    """Remove digits and extension to recover streamer name from clip filename."""
    return "".join(ch for ch in filename.strip(".mp4") if not ch.isdigit())


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
    current_video_length = 0
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
                print(file)

                if os.path.splitext(file)[1] == ".mp4":
                    file_path = os.path.join(root, file)
                    print(file_path)
                    video = VideoFileClip(file_path, target_resolution=target_resolution)
                    L.append(
                        video.with_start(current_video_length - files.index(file)).with_effects(
                            [SlideIn(1, "bottom")]
                        )
                    )
                    print(file)
                    # time stamp handler
                    current_video_length = int(current_video_length)
                    timestamp = f"{current_video_length // 60}:{current_video_length % 60:02d}"
                    streamer_name = _extract_streamer_name(file)
                    time_stamps_file.write(f"{timestamp} - {streamer_name}\n")
                    current_video_length += video.duration - 2
                    # streamer link handler
                    if streamer_name not in streamers:
                        streamer_links_file.write(
                            f"{streamer_name}: https://www.twitch.tv/{streamer_name}\n"
                        )
                        streamers.append(streamer_name)
                    if current_video_length >= max_length_seconds:
                        break
    if not L:
        print("No clips found to compile.")
        return
    final_clip = [CompositeVideoClip(L)]
    print(current_video_length)
    concatenate_videoclips(final_clip, padding=-1).write_videofile(
        os.path.join(full_videos_dir, "%s.mp4" % name),
        fps=60, remove_temp=True, threads=12)


if __name__ == "__main__":
    from datetime import date

    """testing = ImageClip("test.png").set_duration(3)
    testing.write_videofile("testing.mp4",
                            fps=60, remove_temp=True, threads=8)"""

    compile("video1" + str(date.today()))
