"""
Clip metadata models and JSON sidecar persistence.

Pre-download: ClipRef. Post-download: ClipAsset.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def parse_views(text: str) -> Optional[int]:
    """
    Parse view count string to int. Handles K and M suffixes.

    Examples:
        "45" -> 45
        "1.2K" -> 1200
        "2.5M" -> 2500000
        "" -> None
    """
    if not text or not text.strip():
        return None
    text = text.strip().upper().replace(",", "")
    match = re.match(r"^([\d.]+)\s*([KM])?$", text)
    if not match:
        return None
    num_str, suffix = match.groups()
    try:
        value = float(num_str)
    except ValueError:
        return None
    if suffix == "K":
        value *= 1000
    elif suffix == "M":
        value *= 1_000_000
    return int(value)


@dataclass
class ClipRef:
    """Pre-download clip reference from scraping."""

    clip_url: str
    streamer: str = ""
    views: Optional[int] = None
    title: Optional[str] = None

    @classmethod
    def from_url(cls, url: str) -> "ClipRef":
        """Adapter: create ClipRef from URL string for backward compatibility."""
        return cls(clip_url=url, streamer="")


@dataclass
class ClipAsset:
    """Post-download clip with paths and metadata."""

    clip_ref: ClipRef
    mp4_url: str
    output_path: str
    downloaded_at: str  # ISO 8601
    duration_s: Optional[float] = None
    created_at: Optional[str] = None  # ISO 8601 if present

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-suitable dict."""
        return {
            "schema_version": 1,
            "streamer": self.clip_ref.streamer,
            "clip_url": self.clip_ref.clip_url,
            "mp4_url": self.mp4_url,
            "views": self.clip_ref.views,
            "title": self.clip_ref.title,
            "downloaded_at": self.downloaded_at,
            "duration_s": self.duration_s,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClipAsset":
        """Deserialize from dict (e.g. read from JSON). Ignores schema_version for now."""
        ref = ClipRef(
            clip_url=data["clip_url"],
            streamer=data.get("streamer", ""),
            views=data.get("views"),
            title=data.get("title"),
        )
        return cls(
            clip_ref=ref,
            mp4_url=data["mp4_url"],
            output_path=data.get("output_path", ""),
            downloaded_at=data["downloaded_at"],
            duration_s=data.get("duration_s"),
            created_at=data.get("created_at"),
        )


def write_clip_metadata(asset: ClipAsset) -> Path:
    """
    Write clip metadata JSON sidecar next to the mp4.

    If output_path is /path/to/clip.mp4, writes /path/to/clip.json.
    Writes to .json.tmp then renames to .json for atomicity.
    Returns the path to the written JSON file.
    """
    mp4_path = Path(asset.output_path)
    json_path = mp4_path.with_suffix(".json")
    tmp_path = json_path.with_suffix(".json.tmp")
    data = asset.to_dict()
    data["output_path"] = asset.output_path
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp_path.replace(json_path)
    return json_path


def read_clip_metadata(path: Path) -> ClipAsset:
    """
    Read clip metadata from JSON sidecar.

    Path can be .json or .mp4; if .mp4, reads corresponding .json.
    """
    p = Path(path)
    if p.suffix.lower() == ".mp4":
        p = p.with_suffix(".json")
    if p.suffix.lower() != ".json":
        p = Path(str(p) + ".json")
    data = json.loads(p.read_text(encoding="utf-8"))
    if "output_path" not in data and p.suffix == ".json":
        data["output_path"] = str(p.with_suffix(".mp4"))
    return ClipAsset.from_dict(data)
