"""
Test Plan
- Partitions: valid/invalid VodJobParams, ChatMessage, Segment, VodAsset structure
- Boundaries: empty url/message, zero/negative timing values, optional max_segments
- Failure modes: invalid constructor inputs raise ValueError

Covers: TODO-VOD-001
"""

import pytest

from backend.vod_models import ChatMessage, Segment, VodAsset, VodJobParams


def test_vod_job_params_valid_defaults() -> None:
    """Validation: required URL + defaults create valid params."""
    params = VodJobParams(vod_url="https://twitch.tv/videos/123")
    assert params.output_dir == "."
    assert params.keywords == []
    assert params.spike_window_seconds == 30
    assert params.segment_padding_seconds == 15
    assert params.max_segments is None


def test_vod_job_params_invalid_url() -> None:
    """Defect: empty and whitespace-only URL are rejected."""
    with pytest.raises(ValueError, match="vod_url"):
        VodJobParams(vod_url="")
    with pytest.raises(ValueError, match="vod_url"):
        VodJobParams(vod_url="   ")


def test_vod_job_params_invalid_window_values() -> None:
    """Boundary/defect: invalid timing and max_segments values are rejected."""
    with pytest.raises(ValueError, match="spike_window_seconds"):
        VodJobParams(vod_url="https://twitch.tv/videos/1", spike_window_seconds=0)
    with pytest.raises(ValueError, match="spike_window_seconds"):
        VodJobParams(vod_url="https://twitch.tv/videos/1", spike_window_seconds=-1)
    with pytest.raises(ValueError, match="segment_padding_seconds"):
        VodJobParams(vod_url="https://twitch.tv/videos/1", segment_padding_seconds=-1)
    with pytest.raises(ValueError, match="max_segments"):
        VodJobParams(vod_url="https://twitch.tv/videos/1", max_segments=0)
    with pytest.raises(ValueError, match="max_segments"):
        VodJobParams(vod_url="https://twitch.tv/videos/1", max_segments=-5)


def test_chat_message_validation() -> None:
    """Boundary/defect: timestamp and message validation for chat entries."""
    valid = ChatMessage(timestamp_s=0.0, message="pog")
    assert valid.timestamp_s == pytest.approx(0.0)
    assert valid.message == "pog"

    with pytest.raises(ValueError, match="timestamp_s"):
        ChatMessage(timestamp_s=-0.1, message="oops")
    with pytest.raises(ValueError, match="message"):
        ChatMessage(timestamp_s=1.0, message="")
    with pytest.raises(ValueError, match="message"):
        ChatMessage(timestamp_s=1.0, message="   ")


def test_segment_validation() -> None:
    """Boundary/defect: segment fields enforce valid time and non-negative scores."""
    valid = Segment(start_s=1.0, end_s=2.0, spike_score=0.0, keyword_score=0.0)
    assert valid.start_s == pytest.approx(1.0)
    assert valid.end_s == pytest.approx(2.0)

    with pytest.raises(ValueError, match="start_s"):
        Segment(start_s=-1.0, end_s=1.0, spike_score=1.0)
    with pytest.raises(ValueError, match="end_s"):
        Segment(start_s=1.0, end_s=1.0, spike_score=1.0)
    with pytest.raises(ValueError, match="end_s"):
        Segment(start_s=2.0, end_s=1.0, spike_score=1.0)
    with pytest.raises(ValueError, match="spike_score"):
        Segment(start_s=0.0, end_s=1.0, spike_score=-0.1)
    with pytest.raises(ValueError, match="keyword_score"):
        Segment(start_s=0.0, end_s=1.0, spike_score=0.1, keyword_score=-0.1)


def test_segment_total_score_property() -> None:
    """Validation: total_score combines spike and keyword scores."""
    segment = Segment(start_s=10.0, end_s=20.0, spike_score=2.5, keyword_score=1.25)
    assert segment.total_score == pytest.approx(3.75)


def test_vod_asset_defaults_and_structure() -> None:
    """Validation: VodAsset stores structured outputs and optional paths."""
    segment = Segment(start_s=5.0, end_s=8.0, spike_score=4.0)
    asset = VodAsset(vod_path="vod.mp4", chat_path=None, segments=[segment])
    assert asset.vod_path == "vod.mp4"
    assert asset.chat_path is None
    assert asset.montage_path is None
    assert asset.metadata_path is None
    assert len(asset.segments) == 1
    assert asset.segments[0].total_score == pytest.approx(4.0)
