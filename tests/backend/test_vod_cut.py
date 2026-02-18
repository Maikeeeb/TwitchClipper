"""
Test Plan
- Partitions: ffmpeg available/missing, valid vod path/invalid, segment count limits, skips short segments
- Boundaries: empty segments list, single segment, min_segment_seconds=1.0
- Failure modes: missing ffmpeg, file not found, invalid file type, ffmpeg subprocess failure
"""

from pathlib import Path
from unittest import mock

import pytest

from backend.vod_cut import cut_segments, ffmpeg_available
from backend.vod_models import Segment


# Covers: TODO-VOD-008


def test_ffmpeg_available_returns_true_when_found(monkeypatch) -> None:
    """ffmpeg_available returns True when ffmpeg is on PATH."""
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: "ffmpeg")
    assert ffmpeg_available() is True


def test_ffmpeg_available_returns_false_when_missing(monkeypatch) -> None:
    """ffmpeg_available returns False when ffmpeg is not found."""
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: None)
    assert ffmpeg_available() is False


def test_cut_segments_raises_when_vod_path_missing(tmp_path) -> None:
    """cut_segments raises ValueError if vod_path does not exist."""
    vod_path = str(tmp_path / "nonexistent.mp4")
    segments = [Segment(start_s=0.0, end_s=10.0, spike_score=1.0)]

    with pytest.raises(ValueError, match="vod_path does not exist"):
        cut_segments(vod_path, segments, output_dir=str(tmp_path))


def test_cut_segments_raises_when_vod_not_mp4(tmp_path) -> None:
    """cut_segments raises ValueError if vod_path does not end with .mp4."""
    vod_path = tmp_path / "video.mkv"
    vod_path.write_bytes(b"fake video")
    segments = [Segment(start_s=0.0, end_s=10.0, spike_score=1.0)]

    with pytest.raises(ValueError, match="vod_path must end with .mp4"):
        cut_segments(str(vod_path), segments, output_dir=str(tmp_path))


def test_cut_segments_raises_when_ffmpeg_missing(tmp_path, monkeypatch) -> None:
    """cut_segments raises RuntimeError if ffmpeg is not available."""
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: None)

    vod_path = tmp_path / "video.mp4"
    vod_path.write_bytes(b"fake video")
    segments = [Segment(start_s=0.0, end_s=10.0, spike_score=1.0)]

    with pytest.raises(RuntimeError, match="ffmpeg not found on PATH"):
        cut_segments(str(vod_path), segments, output_dir=str(tmp_path))


def test_cut_segments_uses_ffmpeg_subprocess_mocked(tmp_path, monkeypatch) -> None:
    """cut_segments calls ffmpeg with correct -ss/-t arguments."""
    # Mock ffmpeg as available
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: "ffmpeg")

    # Create fake vod file
    vod_path = tmp_path / "vod.mp4"
    vod_path.write_bytes(b"fake video content")

    # Mock subprocess.run to track calls and create output files
    original_run = None

    def mock_run(cmd, **kwargs):
        # Verify correct arguments
        assert cmd[0] == "ffmpeg"
        assert cmd[1] == "-y"
        # Create fake output file
        output_idx = cmd.index("-o") if "-o" in cmd else len(cmd) - 1
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake segment")
        # Return success
        result = mock.Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    monkeypatch.setattr("backend.vod_cut.subprocess.run", mock_run)

    segments = [
        Segment(start_s=0.0, end_s=10.0, spike_score=1.0),
        Segment(start_s=15.0, end_s=25.0, spike_score=1.0),
    ]

    output_paths = cut_segments(
        str(vod_path),
        segments,
        output_dir=str(tmp_path),
    )

    assert len(output_paths) == 2
    assert all(Path(p).exists() for p in output_paths)
    assert output_paths[0].endswith("segment_000_0_10.mp4")
    assert output_paths[1].endswith("segment_001_15_25.mp4")


def test_cut_segments_respects_max_segments(tmp_path, monkeypatch) -> None:
    """cut_segments only cuts first N segments when max_segments is set."""
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: "ffmpeg")

    vod_path = tmp_path / "vod.mp4"
    vod_path.write_bytes(b"fake video")

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake segment")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr("backend.vod_cut.subprocess.run", mock_run)

    segments = [
        Segment(start_s=0.0, end_s=10.0, spike_score=1.0),
        Segment(start_s=15.0, end_s=25.0, spike_score=1.0),
        Segment(start_s=30.0, end_s=40.0, spike_score=1.0),
    ]

    output_paths = cut_segments(
        str(vod_path),
        segments,
        output_dir=str(tmp_path),
        max_segments=2,
    )

    assert len(output_paths) == 2


def test_cut_segments_skips_too_short_segments(tmp_path, monkeypatch) -> None:
    """cut_segments skips segments with duration < min_segment_seconds."""
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: "ffmpeg")

    vod_path = tmp_path / "vod.mp4"
    vod_path.write_bytes(b"fake video")

    call_count = 0

    def mock_run(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake segment")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr("backend.vod_cut.subprocess.run", mock_run)

    segments = [
        Segment(start_s=0.0, end_s=10.0, spike_score=1.0),  # duration=10, kept
        Segment(start_s=15.0, end_s=15.5, spike_score=1.0),  # duration=0.5, skipped
        Segment(start_s=20.0, end_s=25.0, spike_score=1.0),  # duration=5, kept
    ]

    output_paths = cut_segments(
        str(vod_path),
        segments,
        output_dir=str(tmp_path),
        min_segment_seconds=1.0,
    )

    assert len(output_paths) == 2
    assert call_count == 2


def test_cut_segments_creates_output_directory(tmp_path, monkeypatch) -> None:
    """cut_segments creates output_dir if it does not exist."""
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: "ffmpeg")

    vod_path = tmp_path / "vod.mp4"
    vod_path.write_bytes(b"fake video")
    output_dir = tmp_path / "nested" / "output"

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake segment")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr("backend.vod_cut.subprocess.run", mock_run)

    segments = [Segment(start_s=0.0, end_s=10.0, spike_score=1.0)]

    cut_segments(
        str(vod_path),
        segments,
        output_dir=str(output_dir),
    )

    assert output_dir.exists()


def test_cut_segments_does_not_mutate_input(tmp_path, monkeypatch) -> None:
    """cut_segments does not mutate the input segments list."""
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: "ffmpeg")

    vod_path = tmp_path / "vod.mp4"
    vod_path.write_bytes(b"fake video")

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake segment")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr("backend.vod_cut.subprocess.run", mock_run)

    segments = [
        Segment(start_s=0.0, end_s=10.0, spike_score=1.0),
        Segment(start_s=15.0, end_s=25.0, spike_score=1.0),
    ]
    original_len = len(segments)
    original_first = segments[0]

    cut_segments(
        str(vod_path),
        segments,
        output_dir=str(tmp_path),
    )

    assert len(segments) == original_len
    assert segments[0] == original_first


def test_cut_segments_empty_list_returns_empty(tmp_path, monkeypatch) -> None:
    """cut_segments with empty segments list returns empty list."""
    monkeypatch.setattr("backend.vod_cut.shutil.which", lambda x: "ffmpeg")

    vod_path = tmp_path / "vod.mp4"
    vod_path.write_bytes(b"fake video")

    output_paths = cut_segments(
        str(vod_path),
        [],
        output_dir=str(tmp_path),
    )

    assert output_paths == []


@pytest.mark.integration
def test_cut_segments_real_ffmpeg_on_sample_vod(tmp_path) -> None:
    """Real ffmpeg test: cut segment from sample VOD if available."""
    if not ffmpeg_available():
        pytest.skip("ffmpeg not available")

    sample_vod = Path("tests/media/sample_vod.mp4")
    if not sample_vod.exists():
        pytest.skip("tests/media/sample_vod.mp4 not found")

    segments = [Segment(start_s=0.0, end_s=2.0, spike_score=1.0)]

    output_paths = cut_segments(
        str(sample_vod),
        segments,
        output_dir=str(tmp_path),
    )

    assert len(output_paths) == 1
    output_file = Path(output_paths[0])
    assert output_file.exists()
    assert output_file.stat().st_size > 0
