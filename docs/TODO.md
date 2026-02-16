# Backend TODOs (Prioritized)

For product direction and phased deliverables (ranking, job queue, VOD highlights, persistence), see [docs/roadmap.md](docs/roadmap.md).

# Epics

> Rule: Only work on ONE ticket at a time. Do not implement multiple TODO-* items in a single change.

## EPIC: Architecture foundations
- [ ] TODO-ARCH-001 Define shared data models for Clip, Segment, Job
- [ ] TODO-ARCH-002 Define scoring interface (so clip and segment scoring share logic)

## EPIC: Clip filtering and ranking (works for current clips)
- [x] TODO-RANK-001 Define a clip scoring model (views, recency, length, simple bonuses)
- [x] TODO-RANK-002 Implement clip ranking function (input list of clips -> sorted list)
- [x] TODO-RANK-003 Implement filtering rules (remove near-duplicates, min/max duration)
- [x] TODO-RANK-004 Wire ranking into existing pipeline (pick top N before montage)
- [x] TODO-RANK-006: Per streamer candidate selection (top K per streamer) then global rank
- [x] TODO-DUR-001 — Compute and persist duration_s for each downloaded clip.
- [x] TODO-SELECT-001 — Select ranked clips to hit a target montage duration range (default 8–10 minutes).

## EPIC: Job queue and background worker
- [x] TODO-JOBS-001 Define job states and job data model (queued running done failed)
- [x] TODO-JOBS-002 Implement in memory job queue
- [x] TODO-JOBS-003 Implement worker loop that runs jobs
- [x] TODO-JOBS-004 Add API endpoints
- [x] TODO-JOBS-005 Add tests for job state transitions (end-to-end through API + worker).

# EPIC: VOD + Chat auto highlights

## Phase 1 — Data Contracts (No I/O, No Network)

- [ ] TODO-VOD-001 Define VOD job data model (inputs, outputs, metadata structure)
  - Define VodJobParams (vod_url OR vod_id, output_dir, optional keyword list)
  - Define VodAsset (vod_path, chat_path, segments, metadata json schema)
  - Define Segment model (start_s, end_s, spike_score, keyword_score, total_score)
  - No downloading yet — pure data structure only
  - Add unit tests for model validation

## Phase 2 — Chat Analysis (Pure Logic, Fully Testable Offline)

- [ ] TODO-VOD-002 Implement chat spike detector (messages per second)
  - Input: list of (timestamp, message)
  - Output: list of spike windows (timestamp buckets with counts)
  - Deterministic and offline
  - Add strong unit tests (normal, empty, edge cases)

- [ ] TODO-VOD-003 Implement segment generator (spike → time window)
  - Convert spike timestamps into (start_s, end_s)
  - Configurable window size (e.g., ±15s around spike)
  - Merge overlapping windows
  - Unit tests required

- [ ] TODO-VOD-004 Implement segment ranking
  - Score based on spike strength (primary signal)
  - Optional keyword bonus (similar to clip scoring)
  - Sort highest first
  - Add ranking unit tests

## Phase 3 — Chat & VOD I/O (Still Separate from Worker)

- [ ] TODO-VOD-005 Implement chat log importer
  - Accept local chat JSON or raw file
  - Parse into structured (timestamp, message)
  - No network required yet
  - Add parsing tests

- [ ] TODO-VOD-006 Implement VOD downloader
  - Download full VOD mp4 to disk
  - Store path in VodAsset
  - Graceful failure handling
  - Do NOT cut segments yet

## Phase 4 — Video Processing (Heavy I/O)

- [ ] TODO-VOD-007 Cut segments from VOD using ffmpeg
  - Input: VOD mp4 + ranked segments
  - Output: individual mp4 clips
  - Ensure no segment exceeds VOD bounds
  - Add basic integration tests with synthetic mp4

- [ ] TODO-VOD-008 Compile montage from generated segments
  - Reuse existing montage pipeline logic
  - Respect duration window (8–10 minutes)
  - Store final montage path in VodAsset metadata

## Phase 5 — Job Integration

- [ ] TODO-VOD-009 Add vod_highlights job type
  - Register handler in backend/worker.py
  - Params: vod_url (or id), output_dir, optional keywords
  - Worker should:
      1) Download VOD
      2) Load/import chat
      3) Detect spikes
      4) Generate + rank segments
      5) Cut segments
      6) Compile montage
  - Update job.result with output paths and counts

- [ ] TODO-VOD-010 Add end-to-end API test for vod_highlights job
  - Use fake chat data
  - Use synthetic test mp4
  - Ensure QUEUED → RUNNING → DONE flow works


## EPIC: Database persistence
- [ ] TODO-DB-001 Add SQLite persistence for jobs and outputs
- [ ] TODO-DB-002 Store job status updates during runs
- [ ] TODO-DB-003 Store final outputs and metadata paths
- [ ] TODO-DB-004 Add tests for persistence layer

# P0 (Fix first)
- Add explicit validation for streamer name input and empty clip lists.
- Ensure compilation fails gracefully when clips are corrupted or missing.

# P1 (High priority)
- Introduce a config module for paths, timeouts, max clips, and output directories.
- Replace fragile filename parsing with explicit metadata storage (JSON or CSV).
- Add logging instead of `print()` for scraper/compile pipelines.
- Add headless mode and configurable Firefox profile options.

# P2 (Nice to have)
- Add API endpoints to trigger scraping/compilation and report status.
- Add a CLI wrapper with options (streamer list, max clips, output dir).
- Add caching of downloaded clips to avoid repeat downloads.
- Add a lightweight UI to monitor compilation status.

# Test Coverage Mapping
- TODO-TEST-API-HEALTH: Validate health endpoint responses and method errors.
- TODO-TEST-CLIPS-GETCLIPS: Verify clip scraping/download behavior and edge cases.
- TODO-TEST-CLIPS-DOWNLOAD: Validate download_clip success and failure modes.
- TODO-TEST-CLIPS-EXTRACT: Validate extract_mp4_url_from_html parsing behavior.
- TODO-TEST-IMPORTS: Ensure backend modules import and expose expected callables.
- TODO-TEST-ONEVIDEO-COMPILE: Validate compile output creation and no-clip behavior.
- TODO-TEST-OVERLAY: Validate render_overlay parameter handling and failure mode.
- TODO-TEST-TRANSITION: Validate oneTransition output path handling and errors.

# Completed
- Stabilized Twitch clip selectors with fallback strategies in `backend/clips.py`.
- Added retry/skip logic for missing/duplicate video sources.
- Added a `download_clip()` helper to resolve MP4 URLs and download clips.
- Added integration coverage for real Twitch download when enabled.
