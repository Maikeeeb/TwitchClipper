from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.io.VideoFileClip import VideoFileClip


def render_overlay(source_path, output_path, text, position="center", duration=30, fps=30):
    """Render a simple text overlay onto a video clip."""
    clip = VideoFileClip(source_path)
    overlay_text = (
        TextClip(text=text, font_size=12, color="white")
        .with_position(position)
        .with_duration(duration)
    )
    final_clip = CompositeVideoClip([clip, overlay_text])
    final_clip.write_videofile(output_path, fps=fps)


if __name__ == "__main__":
    render_overlay("input.mp4", "test.mp4", "some text")
