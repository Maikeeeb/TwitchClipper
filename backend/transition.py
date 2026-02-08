import os

from moviepy.video.VideoClip import TextClip
from moviepy.video.fx.FadeIn import FadeIn
from moviepy.video.fx.FadeOut import FadeOut


def oneTransition(clipName, tranName, output_dir=None):
    """Create a simple text transition clip."""
    output_dir = output_dir or ""
    print(tranName)
    (
        TextClip(
            text=clipName,
            font_size=50,
            color="white",
            size=(1920, 1080),
            bg_color="black",
            method="label",
        )
        .with_duration(3)
        .with_effects([FadeOut(0.5), FadeIn(0.5)])
        .write_videofile(
            os.path.join(output_dir, f"{str(tranName).strip()}.mp4"),
            fps=60,
            logger=None,
        )
    )


if __name__ == "__main__":
    oneTransition("hello", "1")
