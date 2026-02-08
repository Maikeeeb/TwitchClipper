"""
Test Plan
- Partitions: compile with clips, compile with no clips
- Boundaries: max_length_seconds stops after first clip
- Failure modes: missing clips results in no output
"""

from pathlib import Path

import pytest
from moviepy.video.VideoClip import ColorClip

from backend import oneVideo
from backend.oneVideo import compile as compile_clips
from backend.oneVideo import _extract_streamer_name


def _write_test_clip(path: Path) -> None:
    clip = ColorClip(size=(64, 64), color=(255, 0, 0)).with_duration(1)
    clip.write_videofile(str(path), fps=24, codec="libx264", audio=False, logger=None)


@pytest.mark.integration
def test_compile_creates_output(tmp_path: Path) -> None:
    # Covers: TODO-TEST-ONEVIDEO-COMPILE
    current_videos_dir = tmp_path / "currentVideos"
    full_videos_dir = tmp_path / "fullVideos"
    current_videos_dir.mkdir()
    full_videos_dir.mkdir()

    try:
        _write_test_clip(current_videos_dir / "1000tester0.mp4")
        _write_test_clip(current_videos_dir / "0900tester0.mp4")
    except OSError as exc:
        pytest.skip(f"MoviePy/ffmpeg not available: {exc}")

    time_stamps_path = tmp_path / "time_stamps"
    streamer_links_path = tmp_path / "streamer_links"
    output_name = "test_compilation"

    compile_clips(
        output_name,
        current_videos_dir=str(current_videos_dir),
        full_videos_dir=str(full_videos_dir),
        time_stamps_path=str(time_stamps_path),
        streamer_links_path=str(streamer_links_path),
        max_length_seconds=5,
        target_resolution=(64, 64),
    )

    output_file = full_videos_dir / f"{output_name}.mp4"
    assert output_file.exists()
    assert time_stamps_path.exists()
    assert streamer_links_path.exists()


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("123streamer0.mp4", "streamer"),
        ("0042alpha99.mp4", "alpha"),
        ("beta777.mp4", "beta"),
        ("no_digits.mp4", "no_digits"),
    ],
)
def test_extract_streamer_name(filename: str, expected: str) -> None:
    # Covers: TODO-TEST-ONEVIDEO-COMPILE
    assert _extract_streamer_name(filename) == expected


def test_compile_with_no_clips(tmp_path: Path) -> None:
    # Covers: TODO-TEST-ONEVIDEO-COMPILE
    current_videos_dir = tmp_path / "currentVideos"
    full_videos_dir = tmp_path / "fullVideos"
    current_videos_dir.mkdir()
    full_videos_dir.mkdir()

    output_name = "empty_compilation"
    compile_clips(
        output_name,
        current_videos_dir=str(current_videos_dir),
        full_videos_dir=str(full_videos_dir),
        time_stamps_path=str(tmp_path / "time_stamps"),
        streamer_links_path=str(tmp_path / "streamer_links"),
        max_length_seconds=5,
        target_resolution=(64, 64),
    )

    time_stamps_path = tmp_path / "time_stamps"
    streamer_links_path = tmp_path / "streamer_links"
    assert not (full_videos_dir / f"{output_name}.mp4").exists()
    assert time_stamps_path.exists()
    assert streamer_links_path.exists()
    assert time_stamps_path.read_text() == ""
    assert streamer_links_path.read_text() == ""


def test_compile_stops_at_max_length_boundary(tmp_path: Path, monkeypatch) -> None:
    # Covers: TODO-TEST-ONEVIDEO-COMPILE
    current_videos_dir = tmp_path / "currentVideos"
    full_videos_dir = tmp_path / "fullVideos"
    current_videos_dir.mkdir()
    full_videos_dir.mkdir()

    for filename in ["1000alpha0.mp4", "0900beta0.mp4"]:
        (current_videos_dir / filename).write_text("stub")

    class _DummyClip:
        duration = 3

        def with_start(self, *_args, **_kwargs):
            return self

        def with_effects(self, *_args, **_kwargs):
            return self

    class _DummyConcat:
        def write_videofile(self, output_path, **_kwargs):
            Path(output_path).write_text("compiled")

    monkeypatch.setattr(oneVideo, "VideoFileClip", lambda *_args, **_kwargs: _DummyClip())
    monkeypatch.setattr(oneVideo, "CompositeVideoClip", lambda clips: clips)
    monkeypatch.setattr(oneVideo, "concatenate_videoclips", lambda *_args, **_kwargs: _DummyConcat())

    time_stamps_path = tmp_path / "time_stamps"
    streamer_links_path = tmp_path / "streamer_links"

    compile_clips(
        "boundary_compilation",
        current_videos_dir=str(current_videos_dir),
        full_videos_dir=str(full_videos_dir),
        time_stamps_path=str(time_stamps_path),
        streamer_links_path=str(streamer_links_path),
        max_length_seconds=1,
        target_resolution=(64, 64),
    )

    assert (full_videos_dir / "boundary_compilation.mp4").exists()
    assert time_stamps_path.read_text().count("\n") == 1
    assert streamer_links_path.read_text().count("\n") == 1
