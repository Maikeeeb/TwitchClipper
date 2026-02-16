"""
Clip scoring model (metadata-only).

Scoring uses ClipRef: views (log-scaled) and optional title keyword bonus.
No file I/O or MP4 reading.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from backend.clip_models import ClipRef


def score_clip(
    ref: ClipRef,
    *,
    now: datetime,
    keywords: Optional[list[str]] = None,
    keyword_bonus: float = 5.0,
    keyword_cap: float = 15.0,
) -> float:
    """
    Compute a numeric score for a clip from ClipRef metadata only.

    Formula:
    - Views (main signal): ln(1 + views) using math.log1p (natural log). Missing/negative
      views treated as 0. Use log10 if "log10 feel" desired; update tests accordingly.
    - Keyword bonus: small bonus per matching keyword in title (case-insensitive),
      capped at keyword_cap total. Missing title yields no bonus.
    - Tradeoff: ln(10001)≈9.2; default keyword_cap=15 can overpower views for medium
      clips. For views-dominant, consider keyword_bonus=0.3, keyword_cap=1.0.

    Higher score = better candidate. All inputs from metadata; no file/network access.
    The now parameter enables deterministic tests; reserved for future recency scoring.
    """
    _ = now  # reserved for future recency when ClipRef gains created_at
    keywords = keywords or []
    score = 0.0

    # Views: natural log (ln); missing/None/negative treated as 0
    views = ref.views if ref.views is not None else 0
    score += math.log1p(max(0, views))

    # Title keyword bonus (capped)
    if ref.title and keywords:
        title_lower = ref.title.lower()
        bonus = 0.0
        for kw in keywords:
            if kw.lower() in title_lower:
                bonus += keyword_bonus
        score += min(bonus, keyword_cap)

    return score

def rank_clips(
    clips: list[ClipRef],
    *,
    now: datetime,
    **score_kwargs,
) -> list[ClipRef]:
    """
    Rank clips by score, highest first.

    Uses score_clip for scoring. Tie break: higher views first (None -> 0),
    then clip_url (string order). Does not mutate the input list.
    """
    if not clips:
        return []

    def _sort_key(ref: ClipRef) -> tuple[float, int, str]:
        s = score_clip(ref, now=now, **score_kwargs)
        views = ref.views if ref.views is not None else 0
        return (-s, -max(0, views), ref.clip_url)

    return sorted(clips.copy(), key=_sort_key)
