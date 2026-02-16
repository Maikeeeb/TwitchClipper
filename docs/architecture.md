# Architecture overview (template)

Use this document to describe how the system is structured. Keep it concise and
current; update it when major decisions change.

## Data flow

### Current (clip based)
Inputs are Twitch streamer names listed in the CLI. The backend uses Selenium to discover
recent clips; clips are filtered (deduplicated), ranked by score (views, keywords), and the
top N (default 20) are downloaded. MoviePy assembles clip segments into compiled outputs.
Outputs are stored locally as downloaded clip assets, compiled highlight videos, and metadata
files (time stamps and streamer links).

### Planned (vod + chat based)
Inputs will include a VOD reference (url or id) plus chat log data for the same time range.
The system will:
1) download the vod video
2) fetch or import the chat log
3) detect "high points" using chat volume spikes (messages per second)
4) generate candidate segments (time windows around spikes)
5) rank and filter segments
6) cut segments from the vod and compile a montage
Outputs include compiled highlight videos plus metadata about why each segment was chosen.

## Module boundaries

- `backend/` owns clip discovery, download, compilation, and clip scoring (metadata-only; see `backend/scoring.py`).
- `cli/` owns user-facing scripts (legacy entry points).
- `api/` owns HTTP endpoints (currently `/health` only).
- `frontend/` will own the React UI (planned, not implemented).

## Key invariants

- Deterministic output for identical inputs and configuration.
- Clip compilation should not mutate source assets in place.
- Selenium automation should fail fast with clear errors when VOD data is missing.

## Decision log (optional)

Record important architectural decisions and tradeoffs.
