"""
Test Plan
- Partitions: compile with clips, compile with no clips
- Boundaries: max_length_seconds stops after first clip
- Failure modes: missing/corrupted clips are skipped; zero valid clips raises clear error
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
    with pytest.raises(ValueError, match="No valid clips found to compile"):
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


def test_compile_skips_corrupt_clip_and_reports_it(tmp_path: Path, monkeypatch) -> None:
    # Covers: TODO-TEST-ONEVIDEO-COMPILE
    current_videos_dir = tmp_path / "currentVideos"
    full_videos_dir = tmp_path / "fullVideos"
    current_videos_dir.mkdir()
    full_videos_dir.mkdir()
    (current_videos_dir / "1000good0.mp4").write_text("ok")
    (current_videos_dir / "0900bad0.mp4").write_text("bad")

    class _DummyClip:
        duration = 3

        def with_start(self, *_args, **_kwargs):
            return self

        def with_effects(self, *_args, **_kwargs):
            return self

        def close(self):
            return None

    class _DummyConcat:
        def write_videofile(self, output_path, **_kwargs):
            Path(output_path).write_text("compiled")

    def _fake_video_file_clip(path, **_kwargs):
        if str(path).endswith("0900bad0.mp4"):
            raise OSError("corrupted source")
        return _DummyClip()

    monkeypatch.setattr(oneVideo, "VideoFileClip", _fake_video_file_clip)
    monkeypatch.setattr(oneVideo, "CompositeVideoClip", lambda clips: clips)
    monkeypatch.setattr(oneVideo, "concatenate_videoclips", lambda *_args, **_kwargs: _DummyConcat())

    report = compile_clips(
        "skip_report_compilation",
        current_videos_dir=str(current_videos_dir),
        full_videos_dir=str(full_videos_dir),
        time_stamps_path=str(tmp_path / "time_stamps"),
        streamer_links_path=str(tmp_path / "streamer_links"),
        max_length_seconds=10,
        target_resolution=(64, 64),
    )

    assert (full_videos_dir / "skip_report_compilation.mp4").exists()
    assert report["compiled_clips"] == 1
    assert len(report["skipped_clips"]) == 1
    assert "0900bad0.mp4" in report["skipped_clips"][0]["file_path"]


def test_compile_prefers_sidecar_metadata_over_filename(tmp_path: Path, monkeypatch) -> None:
    # Covers: TODO-TEST-ONEVIDEO-COMPILE
    current_videos_dir = tmp_path / "currentVideos"
    full_videos_dir = tmp_path / "fullVideos"
    current_videos_dir.mkdir()
    full_videos_dir.mkdir()
    clip_path = current_videos_dir / "123legacyname0.mp4"
    clip_path.write_text("stub")
    clip_path.with_suffix(".json").write_text(
        """
{
  "schema_version": 1,
  "streamer": "sidecar_streamer",
  "clip_url": "https://www.twitch.tv/sidecar_streamer/clip/slug",
  "mp4_url": "https://cdn.example.com/clip.mp4",
  "output_path": "ignored",
  "downloaded_at": "2025-01-01T00:00:00Z"
}
""".strip()
    )

    class _DummyClip:
        duration = 3

        def with_start(self, *_args, **_kwargs):
            return self

        def with_effects(self, *_args, **_kwargs):
            return self

        def close(self):
            return None

    class _DummyConcat:
        def write_videofile(self, output_path, **_kwargs):
            Path(output_path).write_text("compiled")

    monkeypatch.setattr(oneVideo, "VideoFileClip", lambda *_args, **_kwargs: _DummyClip())
    monkeypatch.setattr(oneVideo, "CompositeVideoClip", lambda clips: clips)
    monkeypatch.setattr(oneVideo, "concatenate_videoclips", lambda *_args, **_kwargs: _DummyConcat())

    time_stamps_path = tmp_path / "time_stamps"
    streamer_links_path = tmp_path / "streamer_links"
    compile_clips(
        "sidecar_metadata_compilation",
        current_videos_dir=str(current_videos_dir),
        full_videos_dir=str(full_videos_dir),
        time_stamps_path=str(time_stamps_path),
        streamer_links_path=str(streamer_links_path),
        max_length_seconds=10,
        target_resolution=(64, 64),
    )

    assert "sidecar_streamer" in time_stamps_path.read_text()
    assert "https://www.twitch.tv/sidecar_streamer/clip/slug" in streamer_links_path.read_text()


def test_compile_falls_back_to_filename_when_sidecar_missing(tmp_path: Path, monkeypatch) -> None:
    # Covers: TODO-TEST-ONEVIDEO-COMPILE
    current_videos_dir = tmp_path / "currentVideos"
    full_videos_dir = tmp_path / "fullVideos"
    current_videos_dir.mkdir()
    full_videos_dir.mkdir()
    (current_videos_dir / "123fallback0.mp4").write_text("stub")

    class _DummyClip:
        duration = 3

        def with_start(self, *_args, **_kwargs):
            return self

        def with_effects(self, *_args, **_kwargs):
            return self

        def close(self):
            return None

    class _DummyConcat:
        def write_videofile(self, output_path, **_kwargs):
            Path(output_path).write_text("compiled")

    monkeypatch.setattr(oneVideo, "VideoFileClip", lambda *_args, **_kwargs: _DummyClip())
    monkeypatch.setattr(oneVideo, "CompositeVideoClip", lambda clips: clips)
    monkeypatch.setattr(oneVideo, "concatenate_videoclips", lambda *_args, **_kwargs: _DummyConcat())

    time_stamps_path = tmp_path / "time_stamps"
    streamer_links_path = tmp_path / "streamer_links"
    compile_clips(
        "fallback_metadata_compilation",
        current_videos_dir=str(current_videos_dir),
        full_videos_dir=str(full_videos_dir),
        time_stamps_path=str(time_stamps_path),
        streamer_links_path=str(streamer_links_path),
        max_length_seconds=10,
        target_resolution=(64, 64),
    )

    assert "fallback" in time_stamps_path.read_text()
    assert "https://www.twitch.tv/fallback" in streamer_links_path.read_text()
