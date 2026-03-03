"""
Shared runtime configuration defaults.

This module centralizes default paths, limits, and timeout values so API/worker/backend
callers can import one source of truth. Keep values conservative and backward-compatible.
"""

from __future__ import annotations

import os

# Paths / output directories
DEFAULT_OUTPUT_DIR = "."
DEFAULT_CURRENT_VIDEOS_DIR = "."
DEFAULT_DB_PATH = "./data/twitchclipper.sqlite3"

# Clip pipeline defaults
DEFAULT_MAX_CLIPS = 20
DEFAULT_SCRAPE_POOL_SIZE = 50
DEFAULT_PER_STREAMER_K = 10

# Timeout defaults
DEFAULT_HTTP_TIMEOUT_SECONDS = 30
DEFAULT_CLIP_WAIT_SECONDS = 560
DEFAULT_DOWNLOAD_WAIT_SECONDS = 30
DEFAULT_URL_OPEN_TIMEOUT_SECONDS = 15
DEFAULT_TWITCH_GQL_TIMEOUT_SECONDS = 20

# API request model defaults
API_DEFAULT_VOD_MIN_COUNT = 1
API_DEFAULT_SEGMENT_PADDING_SECONDS = 20

# Worker fallback defaults (kept as-is to avoid behavior changes)
WORKER_DEFAULT_VOD_MIN_COUNT = 5
WORKER_DEFAULT_SEGMENT_PADDING_SECONDS = 15


def env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
