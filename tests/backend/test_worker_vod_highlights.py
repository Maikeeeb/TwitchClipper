"""
Test Plan
- Partitions: full pipeline orchestration, local chat_path flow, vod_id fallback
- Boundaries: optional keywords omitted (defaults to empty list)
- Failure modes: missing vod_url/vod_id validation

Covers: TODO-VOD-010
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from backend.jobs import Job
from backend.vod_models import Segment
from backend.worker import _default_vod_highlights_handler, default_handlers


def test_default_handlers_registers_vod_highlights() -> None:
    """Validation: worker built-ins include vod_highlights handler."""
    handlers = default_handlers()
    assert "vod_highlights" in handlers


def test_vod_highlights_handler_orchestrates_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation: handler runs all stages and returns expected result contract."""
    calls: list[str] = []

    class _Asset:
        def __init__(self) -> None:
            self.vod_path = "/tmp/output/vod.mp4"
            self.metadata_path = "/tmp/output/vod.json"

    def _mock_download(vod_url: str, *, output_dir: str, quality: str = "480p") -> _Asset:
        calls.append("download")
        assert vod_url == "https://www.twitch.tv/videos/123"
        assert output_dir == "/tmp/output"
        assert quality == "480p"
        return _Asset()

    def _mock_fetch(vod_url_or_id: str, out_path: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append("fetch_chat")
        assert vod_url_or_id == "https://www.twitch.tv/videos/123"
        assert kwargs["max_pages"] is None
        return {"out_path": str(out_path)}

    def _mock_rank(chat_path: str, **kwargs: Any) -> list[Segment]:
        calls.append("rank_segments")
        assert chat_path.endswith("chat.jsonl")
        assert kwargs["bucket_seconds"] == 30
        assert kwargs["min_count"] == 5
        assert kwargs["padding_seconds"] == 15
        assert kwargs["keywords"] == ["pog"]
        return [
            Segment(start_s=10.0, end_s=20.0, spike_score=3.0),
            Segment(start_s=30.0, end_s=39.5, spike_score=2.0),
        ]

    def _mock_cut(
        vod_path: str,
        segments: list[Segment],
        *,
        output_dir: str,
        max_segments: int | None = None,
        min_segment_seconds: float = 1.0,
    ) -> list[str]:
        calls.append("cut_segments")
        assert vod_path == "/tmp/output/vod.mp4"
        assert len(segments) == 2
        assert output_dir == os.path.join("/tmp/output", "clips")
        assert max_segments is None
        assert min_segment_seconds == pytest.approx(1.0)
        return ["/tmp/output/clips/segment_000_10_20.mp4"]

    def _mock_select(
        ranked_segments: list[Segment],
        *,
        min_seconds: int = 480,
        max_seconds: int = 600,
        max_segment_seconds: float = 120.0,
        diversity_windows: int = 8,
    ) -> list[Segment]:
        calls.append("select_segments")
        assert len(ranked_segments) == 2
        assert min_seconds == 480
        assert max_seconds == 600
        assert max_segment_seconds == pytest.approx(120.0)
        assert diversity_windows == 8
        return ranked_segments

    def _mock_montage(
        segment_paths: list[str],
        *,
        output_path: str,
        min_seconds: int = 480,
        max_seconds: int = 600,
    ) -> str:
        calls.append("compile_montage")
        assert len(segment_paths) == 1
        assert output_path == os.path.join("/tmp/output", "montage.mp4")
        assert min_seconds == 480
        assert max_seconds == 600
        return output_path

    monkeypatch.setattr("backend.vod_download.download_vod", _mock_download)
    monkeypatch.setattr("backend.vod_chat_fetch.fetch_vod_chat_to_jsonl", _mock_fetch)
    monkeypatch.setattr("backend.vod_chat_pipeline.chat_file_to_ranked_segments", _mock_rank)
    monkeypatch.setattr("backend.selection.select_non_overlapping_segments_for_duration", _mock_select)
    monkeypatch.setattr("backend.vod_cut.cut_segments", _mock_cut)
    monkeypatch.setattr("backend.vod_montage.compile_vod_montage", _mock_montage)

    job = Job(
        type="vod_highlights",
        params={
            "vod_url": "https://www.twitch.tv/videos/123",
            "output_dir": "/tmp/output",
            "keywords": ["pog"],
        },
    )
    result = _default_vod_highlights_handler(job)

    assert calls == [
        "download",
        "fetch_chat",
        "rank_segments",
        "select_segments",
        "cut_segments",
        "compile_montage",
    ]
    assert result["vod_path"] == "/tmp/output/vod.mp4"
    assert result["chat_path"].endswith("chat.jsonl")
    assert result["segments_count"] == 2
    assert result["clips_count"] == 1
    assert result["montage_path"] == os.path.join("/tmp/output", "montage.mp4")
    assert result["clips_dir"] == os.path.join("/tmp/output", "clips")
    assert result["metadata_path"] == "/tmp/output/vod.json"
    assert result["durations_s"] == [10.0, 9.5]


def test_vod_highlights_handler_uses_local_chat_path_when_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boundary: local chat_path bypasses Twitch web fetch stage."""

    class _Asset:
        vod_path = "/tmp/output/vod.mp4"
        metadata_path = "/tmp/output/vod.json"

    monkeypatch.setattr("backend.vod_download.download_vod", lambda *_args, **_kwargs: _Asset())

    def _fail_if_called(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fetch_vod_chat_to_jsonl should not be called with local chat_path")

    monkeypatch.setattr("backend.vod_chat_fetch.fetch_vod_chat_to_jsonl", _fail_if_called)
    monkeypatch.setattr(
        "backend.vod_chat_pipeline.chat_file_to_ranked_segments",
        lambda chat_path, **_kwargs: [Segment(start_s=0.0, end_s=5.0, spike_score=1.0)]
        if chat_path == "/tmp/local_chat.jsonl"
        else [],
    )
    monkeypatch.setattr(
        "backend.vod_cut.cut_segments",
        lambda *_args, **_kwargs: ["/tmp/output/clips/segment_000_0_5.mp4"],
    )
    monkeypatch.setattr(
        "backend.vod_montage.compile_vod_montage",
        lambda *_args, **_kwargs: "/tmp/output/montage.mp4",
    )

    job = Job(
        type="vod_highlights",
        params={
            "vod_url": "https://www.twitch.tv/videos/123",
            "output_dir": "/tmp/output",
            "chat_path": "/tmp/local_chat.jsonl",
        },
    )
    result = _default_vod_highlights_handler(job)
    assert result["chat_path"] == "/tmp/local_chat.jsonl"


def test_vod_highlights_handler_accepts_vod_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation: vod_id fallback resolves to Twitch VOD URL for download."""
    seen: dict[str, str] = {}

    class _Asset:
        vod_path = "/tmp/output/vod.mp4"
        metadata_path = "/tmp/output/vod.json"

    def _mock_download(vod_url: str, *, output_dir: str, quality: str = "480p") -> _Asset:
        seen["vod_url"] = vod_url
        seen["output_dir"] = output_dir
        seen["quality"] = quality
        return _Asset()

    monkeypatch.setattr("backend.vod_download.download_vod", _mock_download)
    monkeypatch.setattr(
        "backend.vod_chat_fetch.fetch_vod_chat_to_jsonl",
        lambda *_args, **_kwargs: {"out_path": "/tmp/output/chat.jsonl"},
    )
    monkeypatch.setattr(
        "backend.vod_chat_pipeline.chat_file_to_ranked_segments",
        lambda *_args, **_kwargs: [Segment(start_s=5.0, end_s=8.0, spike_score=1.0)],
    )
    monkeypatch.setattr(
        "backend.vod_cut.cut_segments",
        lambda *_args, **_kwargs: ["/tmp/output/clips/segment_000_5_8.mp4"],
    )
    monkeypatch.setattr(
        "backend.vod_montage.compile_vod_montage",
        lambda *_args, **_kwargs: "/tmp/output/montage.mp4",
    )

    job = Job(type="vod_highlights", params={"vod_id": "9999", "output_dir": "/tmp/output"})
    _default_vod_highlights_handler(job)
    assert seen["vod_url"] == "https://www.twitch.tv/videos/9999"
    assert seen["output_dir"] == "/tmp/output"
    assert seen["quality"] == "480p"


def test_vod_highlights_handler_requires_vod_url_or_vod_id() -> None:
    """Defect: missing VOD identifier raises a clear validation error."""
    job = Job(type="vod_highlights", params={"output_dir": "/tmp/output"})
    with pytest.raises(ValueError, match="requires either 'vod_url' or 'vod_id'"):
        _default_vod_highlights_handler(job)
