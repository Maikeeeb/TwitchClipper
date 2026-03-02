"""Small shared scoring helpers used by clip and segment wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class KeywordScoreConfig:
    """Shared keyword-scoring parameters."""

    keywords: list[str] | None
    keyword_bonus: float = 5.0
    keyword_cap: float = 15.0
    case_insensitive: bool = True


def validate_non_negative_keyword_params(keyword_bonus: float, keyword_cap: float) -> None:
    """Validate keyword-scoring params for strict wrappers."""
    if keyword_bonus < 0:
        raise ValueError("keyword_bonus must be >= 0")
    if keyword_cap < 0:
        raise ValueError("keyword_cap must be >= 0")


def compute_keyword_bonus(
    text: str | None,
    config: KeywordScoreConfig,
    *,
    skip_empty_keywords: bool,
) -> float:
    """
    Compute additive keyword bonus with cap, preserving wrapper-defined semantics.
    """
    if text is None or not config.keywords:
        return 0.0

    haystack = text.lower() if config.case_insensitive else text
    bonus = 0.0

    for keyword in config.keywords:
        candidate = keyword
        if skip_empty_keywords and not candidate:
            continue
        needle = candidate.lower() if config.case_insensitive else candidate
        if needle in haystack:
            bonus += config.keyword_bonus

    return min(bonus, config.keyword_cap)


def rank_by_keys(items: Iterable[T], key_fn: Callable[[T], tuple[Any, ...]]) -> list[T]:
    """Return a deterministic sorted list from key tuples."""
    return sorted(items, key=key_fn)
