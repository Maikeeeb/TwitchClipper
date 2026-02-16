"""
Data contracts for VOD + chat highlight pipeline.

This module intentionally contains only typed models and validation.
No I/O, network calls, or processing logic should live here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VodJobParams:
    """Parameters passed to a vod_highlights job."""

    vod_url: str
    output_dir: str = "."
    keywords: list[str] = field(default_factory=list)
    spike_window_seconds: int = 30
    segment_padding_seconds: int = 15
    max_segments: int | None = None

    def __post_init__(self) -> None:
        if not self.vod_url or not self.vod_url.strip():
            raise ValueError("vod_url must be non-empty")
        if self.spike_window_seconds <= 0:
            raise ValueError("spike_window_seconds must be greater than 0")
        if self.segment_padding_seconds < 0:
            raise ValueError("segment_padding_seconds must be >= 0")
        if self.max_segments is not None and self.max_segments <= 0:
            raise ValueError("max_segments must be positive if provided")


@dataclass
class ChatMessage:
    """A parsed chat entry with timestamp from VOD start."""

    timestamp_s: float
    message: str

    def __post_init__(self) -> None:
        if self.timestamp_s < 0:
            raise ValueError("timestamp_s must be >= 0")
        if not self.message or not self.message.strip():
            raise ValueError("message must not be empty")


@dataclass
class Segment:
    """A highlight segment candidate and its scores."""

    start_s: float
    end_s: float
    spike_score: float
    keyword_score: float = 0.0

    def __post_init__(self) -> None:
        if self.start_s < 0:
            raise ValueError("start_s must be >= 0")
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        if self.spike_score < 0:
            raise ValueError("spike_score must be >= 0")
        if self.keyword_score < 0:
            raise ValueError("keyword_score must be >= 0")

    @property
    def total_score(self) -> float:
        return self.spike_score + self.keyword_score


@dataclass
class VodAsset:
    """Artifacts produced by VOD processing."""

    vod_path: str
    chat_path: str | None
    segments: list[Segment] = field(default_factory=list)
    montage_path: str | None = None
    metadata_path: str | None = None
