# Backend Report

This report reflects the current backend as of the latest `master` branch.

## Core orchestration

### `backend/pipeline.py` (clip montage path)
- **What it does:** Orchestrates clip scrape -> filter -> rank -> capped download -> duration-based selection.
- **What works:** Multi-streamer candidate balancing (`PER_STREAMER_K`), deterministic ranking, and cached asset reuse via JSON sidecars (skips re-download when sidecar+mp4 already exist).
- **Known risks:**
  - Twitch site scraping selectors in `backend/clips.py` remain a best-effort dependency.
  - Overlay/remux steps still depend on ffmpeg availability.

### `backend/worker.py` + `backend/job_queue.py`
- **What it does:** Handles queued jobs and executes registered handlers (`clip_montage`, `vod_highlights`).
- **What works:** Job lifecycle transitions (`queued -> running -> done/failed`) and structured result payloads.
- **Known risks:** Current worker is run via API helper (`/jobs/run-next`) or explicit loop; no dedicated long-running process supervisor yet.

## API and persistence surface

### `api/app.py`
- **What it does:** Exposes job endpoints and request validation.
- **What works:** `POST /jobs/clip-montage`, `POST /jobs/vod-highlights`, `POST /jobs`, `GET /jobs/{id}`, and `POST /jobs/run-next`.
- **Known risks:** API is currently backend-first; no frontend-facing auth/rate-limiting layer yet.

### `backend/db/`
- **What it does:** Optional SQLite persistence for jobs and outputs.
- **What works:** When enabled, job reads/writes use SQLite as source of truth.
- **Known risks:** Local SQLite is suitable for single-node/dev workloads; multi-instance coordination is out of scope today.

## VOD highlights pipeline

### `backend/vod_download.py`
- **What it does:** Downloads or resolves VOD media from Twitch/local inputs.
- **What works:** Supports local and URL-based flows with safe defaults.
- **Known risks:** External download tooling/network failures still require retry/observability improvements.

### `backend/vod_chat_fetch.py` and `backend/chat_import.py`
- **What they do:** Fetch Twitch replay chat (best effort) or import local chat logs.
- **What works:** Normalized JSONL flow and offline-import path for deterministic testing.
- **Known risks:** Twitch web endpoint shape can change without notice.

### `backend/vod_chat_pipeline.py`, `backend/chat_spikes.py`, `backend/segment_generator.py`, `backend/segment_scoring.py`, `backend/selection.py`
- **What they do:** Convert chat to spike windows, generate/merge/rank segments, and select final clips to fit target montage duration.
- **What works:** Deterministic ranking with shared scoring primitives and duration-aware selection.
- **Known risks:** Quality depends heavily on chat activity; low-chat streams may under-produce strong candidates.

## Media assembly

### `backend/vod_cut.py` and `backend/vod_montage.py`
- **What they do:** Cut segments from VOD and compile final montage.
- **What works:** Segment bounds validation and reusable montage assembly path.
- **Known risks:** ffmpeg availability and codec edge cases remain operational dependencies.
