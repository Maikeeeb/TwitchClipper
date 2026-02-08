"""
Test Plan
- Partitions: overlay/transition happy path
- Boundaries: custom fps/duration/position, empty output_dir
- Failure modes: propagates MoviePy construction errors
"""

from unittest import mock

import pytest

from backend import overlay, transition


def test_render_overlay_calls_write() -> None:
    # Covers: TODO-TEST-OVERLAY
    with mock.patch("backend.overlay.VideoFileClip") as video_clip, mock.patch(
        "backend.overlay.TextClip"
    ) as text_clip, mock.patch("backend.overlay.CompositeVideoClip") as composite:
        mock_text = mock.Mock()
        mock_text.with_position.return_value = mock_text
        mock_text.with_duration.return_value = mock_text
        text_clip.return_value = mock_text
        composite.return_value.write_videofile = mock.Mock()
        overlay.render_overlay("input.mp4", "output.mp4", "hello")
        composite.return_value.write_videofile.assert_called_once()
        video_clip.assert_called_once_with("input.mp4")
        text_clip.assert_called_once()


def test_one_transition_writes_file() -> None:
    # Covers: TODO-TEST-TRANSITION
    mock_clip = mock.Mock()
    mock_clip.with_duration.return_value = mock_clip
    mock_clip.with_effects.return_value = mock_clip
    mock_clip.write_videofile.return_value = None

    with mock.patch("backend.transition.TextClip", return_value=mock_clip) as text_clip:
        transition.oneTransition("hello", "1", output_dir=".")
        text_clip.assert_called_once()
        mock_clip.write_videofile.assert_called_once()


def test_render_overlay_passes_custom_parameters() -> None:
    # Covers: TODO-TEST-OVERLAY
    with mock.patch("backend.overlay.VideoFileClip") as video_clip, mock.patch(
        "backend.overlay.TextClip"
    ) as text_clip, mock.patch("backend.overlay.CompositeVideoClip") as composite:
        mock_text = mock.Mock()
        mock_text.with_position.return_value = mock_text
        mock_text.with_duration.return_value = mock_text
        text_clip.return_value = mock_text
        composite.return_value.write_videofile = mock.Mock()

        overlay.render_overlay(
            "input.mp4",
            "output.mp4",
            "hello",
            position="top",
            duration=0,
            fps=15,
        )

        mock_text.with_position.assert_called_once_with("top")
        mock_text.with_duration.assert_called_once_with(0)
        composite.return_value.write_videofile.assert_called_once_with("output.mp4", fps=15)
        video_clip.assert_called_once_with("input.mp4")


def test_render_overlay_propagates_video_errors() -> None:
    # Covers: TODO-TEST-OVERLAY
    with mock.patch(
        "backend.overlay.VideoFileClip", side_effect=OSError("cannot read")
    ), mock.patch("backend.overlay.TextClip"), mock.patch(
        "backend.overlay.CompositeVideoClip"
    ):
        with pytest.raises(OSError, match="cannot read"):
            overlay.render_overlay("bad.mp4", "out.mp4", "hello")


def test_one_transition_default_output_dir() -> None:
    # Covers: TODO-TEST-TRANSITION
    mock_clip = mock.Mock()
    mock_clip.with_duration.return_value = mock_clip
    mock_clip.with_effects.return_value = mock_clip
    mock_clip.write_videofile.return_value = None

    with mock.patch("backend.transition.TextClip", return_value=mock_clip):
        transition.oneTransition("hello", "1", output_dir=None)
        mock_clip.write_videofile.assert_called_once()


def test_one_transition_propagates_textclip_errors() -> None:
    # Covers: TODO-TEST-TRANSITION
    with mock.patch(
        "backend.transition.TextClip", side_effect=RuntimeError("boom")
    ) as text_clip:
        with pytest.raises(RuntimeError, match="boom"):
            transition.oneTransition("hello", "1", output_dir=".")
        text_clip.assert_called_once()
