"""Lightweight typed models for persisted DB rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class OutputRecord:
    """Output artifact metadata stored per job."""

    job_id: str
    kind: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
