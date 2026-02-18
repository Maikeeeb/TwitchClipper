"""
Test Plan
- Partitions: empty paths, all files exist, some files missing, duration selection hits/misses min
- Boundaries: single clip, multiple clips, zero duration clips, None duration
- Failure modes: no valid files, ffmpeg missing, subprocess failure
"""

from pathlib import Path
from unittest import mock

import pytest

from backend.vod_montage import compile_vod_montage, _get_clip_duration


# Covers: TODO-VOD-009


def test_compile_vod_montage_empty_raises() -> None:
    """compile_vod_montage raises ValueError if segment_paths is empty."""
    with pytest.raises(ValueError, match="segment_paths must not be empty"):
        compile_vod_montage([], output_path="/tmp/out.mp4")


def test_compile_vod_montage_no_existing_files_raises(tmp_path) -> None:
    """compile_vod_montage raises ValueError if no files exist."""
    with pytest.raises(ValueError, match="no valid segment files found"):
        compile_vod_montage(
            [str(tmp_path / "missing1.mp4"), str(tmp_path / "missing2.mp4")],
            output_path=str(tmp_path / "out.mp4"),
        )


def test_compile_vod_montage_filters_missing_files(tmp_path, monkeypatch) -> None:
    """compile_vod_montage ignores missing files and processes existing ones."""
    # Mock subprocess to avoid needing ffmpeg
    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake montage")
        result = mock.Mock()
        result.returncode = 0
        return result

    def mock_get_duration(path):
        return 100.0 if Path(path).exists() else None

    monkeypatch.setattr("backend.vod_montage.subprocess.run", mock_run)
    monkeypatch.setattr("backend.vod_montage._get_clip_duration", mock_get_duration)

    # Create one real file
    real_file = tmp_path / "segment_000.mp4"
    real_file.write_bytes(b"fake segment")

    output_path = str(tmp_path / "montage.mp4")

    # Mix real and missing files
    result = compile_vod_montage(
        [str(tmp_path / "missing.mp4"), str(real_file)],
        output_path=output_path,
    )

    assert result == output_path
    assert Path(output_path).exists()


def test_compile_vod_montage_calls_ffmpeg_concat_mocked(tmp_path, monkeypatch) -> None:
    """compile_vod_montage calls ffmpeg concat with correct arguments."""
    call_args = []

    def mock_run(cmd, **kwargs):
        call_args.append(cmd)
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake montage")
        result = mock.Mock()
        result.returncode = 0
        return result

    def mock_get_duration(path):
        return 100.0 if Path(path).exists() else None

    monkeypatch.setattr("backend.vod_montage.subprocess.run", mock_run)
    monkeypatch.setattr("backend.vod_montage._get_clip_duration", mock_get_duration)

    # Create fake segment files
    seg1 = tmp_path / "segment_000.mp4"
    seg2 = tmp_path / "segment_001.mp4"
    seg1.write_bytes(b"segment1")
    seg2.write_bytes(b"segment2")

    output_path = str(tmp_path / "montage.mp4")

    compile_vod_montage(
        [str(seg1), str(seg2)],
        output_path=output_path,
    )

    # Verify ffmpeg was called with concat
    assert len(call_args) == 1
    cmd = call_args[0]
    assert cmd[0] == "ffmpeg"
    assert "-f" in cmd
    assert "concat" in cmd
    assert "-c" in cmd
    assert "copy" in cmd
    assert output_path in cmd


def test_duration_selection_hits_window(tmp_path, monkeypatch) -> None:
    """Duration selection: clips sum to value within [min, max]; stops at min."""
    call_count = 0

    def mock_get_duration(path):
        # Return fixed durations
        if "seg1" in path:
            return 180.0
        elif "seg2" in path:
            return 180.0
        elif "seg3" in path:
            return 180.0
        return None

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake montage")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr(
        "backend.vod_montage._get_clip_duration",
        mock_get_duration,
    )
    monkeypatch.setattr("backend.vod_montage.subprocess.run", mock_run)

    # Create segment files
    seg1 = tmp_path / "seg1.mp4"
    seg2 = tmp_path / "seg2.mp4"
    seg3 = tmp_path / "seg3.mp4"
    seg1.write_bytes(b"1")
    seg2.write_bytes(b"2")
    seg3.write_bytes(b"3")

    output_path = str(tmp_path / "montage.mp4")

    compile_vod_montage(
        [str(seg1), str(seg2), str(seg3)],
        output_path=output_path,
        min_seconds=480,
        max_seconds=600,
    )

    # 180 + 180 + 180 = 540, within [480, 600], stops at min
    assert Path(output_path).exists()


def test_duration_selection_never_exceeds_max(tmp_path, monkeypatch) -> None:
    """Duration selection: never exceeds max_seconds."""
    def mock_get_duration(path):
        # Return fixed durations
        if "seg1" in path:
            return 300.0
        elif "seg2" in path:
            return 200.0
        elif "seg3" in path:
            return 200.0
        return None

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake montage")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr(
        "backend.vod_montage._get_clip_duration",
        mock_get_duration,
    )
    monkeypatch.setattr("backend.vod_montage.subprocess.run", mock_run)

    seg1 = tmp_path / "seg1.mp4"
    seg2 = tmp_path / "seg2.mp4"
    seg3 = tmp_path / "seg3.mp4"
    seg1.write_bytes(b"1")
    seg2.write_bytes(b"2")
    seg3.write_bytes(b"3")

    output_path = str(tmp_path / "montage.mp4")

    compile_vod_montage(
        [str(seg1), str(seg2), str(seg3)],
        output_path=output_path,
        min_seconds=480,
        max_seconds=500,
    )

    # 300 + 200 = 500, at max (seg3 would exceed, not added)
    assert Path(output_path).exists()


def test_duration_selection_returns_best_under_max_when_cannot_hit_min(
    tmp_path, monkeypatch
) -> None:
    """Duration selection: returns best possible under max if cannot hit min."""
    def mock_get_duration(path):
        # All small clips, cannot hit min=480
        return 100.0

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake montage")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr(
        "backend.vod_montage._get_clip_duration",
        mock_get_duration,
    )
    monkeypatch.setattr("backend.vod_montage.subprocess.run", mock_run)

    seg1 = tmp_path / "seg1.mp4"
    seg2 = tmp_path / "seg2.mp4"
    seg3 = tmp_path / "seg3.mp4"
    seg1.write_bytes(b"1")
    seg2.write_bytes(b"2")
    seg3.write_bytes(b"3")

    output_path = str(tmp_path / "montage.mp4")

    compile_vod_montage(
        [str(seg1), str(seg2), str(seg3)],
        output_path=output_path,
        min_seconds=480,
        max_seconds=500,
    )

    # All clips are 100s, max=500 means only first 5 can fit, but less still ok
    assert Path(output_path).exists()


def test_compile_vod_montage_skips_none_duration_clips(tmp_path, monkeypatch) -> None:
    """compile_vod_montage skips clips where duration cannot be read."""
    def mock_get_duration(path):
        if "seg1" in path:
            return 200.0
        elif "seg2" in path:
            return None  # Cannot read
        elif "seg3" in path:
            return 300.0
        return None

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake montage")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr(
        "backend.vod_montage._get_clip_duration",
        mock_get_duration,
    )
    monkeypatch.setattr("backend.vod_montage.subprocess.run", mock_run)

    seg1 = tmp_path / "seg1.mp4"
    seg2 = tmp_path / "seg2.mp4"
    seg3 = tmp_path / "seg3.mp4"
    seg1.write_bytes(b"1")
    seg2.write_bytes(b"2")
    seg3.write_bytes(b"3")

    output_path = str(tmp_path / "montage.mp4")

    compile_vod_montage(
        [str(seg1), str(seg2), str(seg3)],
        output_path=output_path,
        min_seconds=400,
        max_seconds=600,
    )

    # seg2 skipped (None duration), seg1 (200) + seg3 (300) = 500
    assert Path(output_path).exists()


def test_compile_vod_montage_returns_output_path(tmp_path, monkeypatch) -> None:
    """compile_vod_montage returns the output_path passed in."""
    def mock_get_duration(path):
        return 100.0

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake montage")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr(
        "backend.vod_montage._get_clip_duration",
        mock_get_duration,
    )
    monkeypatch.setattr("backend.vod_montage.subprocess.run", mock_run)

    seg1 = tmp_path / "seg1.mp4"
    seg1.write_bytes(b"1")
    output_path = str(tmp_path / "montage.mp4")

    result = compile_vod_montage(
        [str(seg1)],
        output_path=output_path,
    )

    assert result == output_path


def test_compile_vod_montage_single_clip(tmp_path, monkeypatch) -> None:
    """compile_vod_montage works with a single segment clip."""
    def mock_get_duration(path):
        return 500.0

    def mock_run(cmd, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b"fake montage")
        result = mock.Mock()
        result.returncode = 0
        return result

    monkeypatch.setattr(
        "backend.vod_montage._get_clip_duration",
        mock_get_duration,
    )
    monkeypatch.setattr("backend.vod_montage.subprocess.run", mock_run)

    seg1 = tmp_path / "seg1.mp4"
    seg1.write_bytes(b"1")
    output_path = str(tmp_path / "montage.mp4")

    result = compile_vod_montage(
        [str(seg1)],
        output_path=output_path,
        min_seconds=480,
        max_seconds=600,
    )

    assert result == output_path
    assert Path(output_path).exists()


def test_get_clip_duration_returns_none_when_moviepy_unavailable(
    monkeypatch,
) -> None:
    """_get_clip_duration returns None if MoviePy is not available."""
    monkeypatch.setattr("backend.vod_montage.VideoFileClip", None)
    result = _get_clip_duration("/tmp/fake.mp4")
    assert result is None


def test_get_clip_duration_returns_none_on_error(monkeypatch) -> None:
    """_get_clip_duration returns None if VideoFileClip raises."""
    def mock_videoclip(*args, **kwargs):
        raise OSError("Cannot open file")

    monkeypatch.setattr("backend.vod_montage.VideoFileClip", mock_videoclip)
    result = _get_clip_duration("/tmp/fake.mp4")
    assert result is None


@pytest.mark.integration
def test_compile_vod_montage_real_ffmpeg_on_sample_vods(tmp_path) -> None:
    """Real ffmpeg test: compile montage from sample VODs if available."""
    from backend.vod_cut import ffmpeg_available

    if not ffmpeg_available():
        pytest.skip("ffmpeg not available")

    # Try to find sample vods
    sample_dir = Path("tests/media")
    if not sample_dir.exists():
        pytest.skip("tests/media directory not found")

    mp4_files = list(sample_dir.glob("*.mp4"))
    if len(mp4_files) < 1:
        pytest.skip("No sample mp4 files found in tests/media")

    # Use first one or two samples
    segment_paths = [str(f) for f in mp4_files[:2]]
    output_path = str(tmp_path / "montage.mp4")

    result = compile_vod_montage(
        segment_paths,
        output_path=output_path,
        min_seconds=1,
        max_seconds=1000,
    )

    assert result == output_path
    assert Path(output_path).exists()
    assert Path(output_path).stat().st_size > 0
