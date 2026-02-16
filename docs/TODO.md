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
- [ ] TODO-JOBS-001 Define job states and job data model (queued running done failed)
- [ ] TODO-JOBS-002 Implement in memory job queue
- [ ] TODO-JOBS-003 Implement worker loop that runs jobs
- [ ] TODO-JOBS-004 Add CLI command to submit job and poll status
- [ ] TODO-JOBS-005 Add tests for job state transitions

## EPIC: VOD + Chat auto highlights
- [ ] TODO-VOD-001 Define inputs and outputs for vod job (paths, metadata files)
- [ ] TODO-VOD-002 Implement vod downloader (save mp4 locally)
- [ ] TODO-VOD-003 Implement chat log fetch or import (save raw chat to file)
- [ ] TODO-VOD-004 Implement chat spike detector (messages per second)
- [ ] TODO-VOD-005 Implement segment generator (spike -> start/end window)
- [ ] TODO-VOD-006 Implement segment ranking (spike score + keyword bonus)
- [ ] TODO-VOD-007 Cut segments from vod using ffmpeg (save as mp4 clips)
- [ ] TODO-VOD-008 Compile montage from generated segments (reuse montage)
- [ ] TODO-VOD-009 End to end CLI command (one command runs pipeline)
- [ ] TODO-VOD-010 Add tests for spike detector and segment generator

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
