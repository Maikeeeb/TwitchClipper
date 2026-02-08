# Architecture overview (template)

Use this document to describe how the system is structured. Keep it concise and
current; update it when major decisions change.

## Data flow

Inputs are Twitch streamer names listed in `cli/mainFile` (legacy script) and
later via the API. The backend uses Selenium to discover recent clips,
downloads MP4 assets, and MoviePy assembles clip segments into compiled outputs.
Outputs are stored locally as downloaded clip assets, compiled highlight
videos, and metadata files (time stamps and streamer links).

## Module boundaries

- `backend/` owns clip discovery, download, and compilation.
- `cli/` owns user-facing scripts (legacy entry points).
- `api/` owns HTTP endpoints (currently `/health` only).
- `frontend/` will own the React UI (planned, not implemented).

## Key invariants

- Deterministic output for identical inputs and configuration.
- Clip compilation should not mutate source assets in place.
- Selenium automation should fail fast with clear errors when VOD data is missing.

## Decision log (optional)

Record important architectural decisions and tradeoffs.
