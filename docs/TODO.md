# Backend TODOs (Prioritized)

## Test Coverage Mapping
- TODO-TEST-API-HEALTH: Validate health endpoint responses and method errors.
- TODO-TEST-CLIPS-GETCLIPS: Verify clip scraping/download behavior and edge cases.
- TODO-TEST-CLIPS-DOWNLOAD: Validate download_clip success and failure modes.
- TODO-TEST-CLIPS-EXTRACT: Validate extract_mp4_url_from_html parsing behavior.
- TODO-TEST-IMPORTS: Ensure backend modules import and expose expected callables.
- TODO-TEST-ONEVIDEO-COMPILE: Validate compile output creation and no-clip behavior.
- TODO-TEST-OVERLAY: Validate render_overlay parameter handling and failure mode.
- TODO-TEST-TRANSITION: Validate oneTransition output path handling and errors.

## P0 (Fix first)
- Add explicit validation for streamer name input and empty clip lists.
- Ensure compilation fails gracefully when clips are corrupted or missing.

## P1 (High priority)
- Introduce a config module for paths, timeouts, max clips, and output directories.
- Replace fragile filename parsing with explicit metadata storage (JSON or CSV).
- Add logging instead of `print()` for scraper/compile pipelines.
- Add headless mode and configurable Firefox profile options.

## P2 (Nice to have)
- Add API endpoints to trigger scraping/compilation and report status.
- Add a CLI wrapper with options (streamer list, max clips, output dir).
- Add caching of downloaded clips to avoid repeat downloads.
- Add a lightweight UI to monitor compilation status.

## Completed
- Stabilized Twitch clip selectors with fallback strategies in `backend/clips.py`.
- Added retry/skip logic for missing/duplicate video sources.
- Added a `download_clip()` helper to resolve MP4 URLs and download clips.
- Added integration coverage for real Twitch download when enabled.
