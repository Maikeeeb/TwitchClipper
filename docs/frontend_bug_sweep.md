# Frontend Unattended Bug Sweep (WPF)

This runbook implements a repeatable unattended bug sweep for the desktop app.
It combines:

- local startup and baseline checks,
- API/runtime gates,
- desktop behavior emulation scenarios,
- strict pass/fail oracles,
- standardized defect capture.

## 1) Local Runbook

Use two terminals.

### Terminal A: API

```powershell
uvicorn api.main:app --reload
```

Expected:

- `GET /health` returns `{"ok": true}`.

### Terminal B: Frontend

```powershell
dotnet build frontend/TwitchClipper.Frontend.sln
dotnet run --project frontend/TwitchClipper.Desktop/TwitchClipper.Desktop.csproj
```

Expected:

- app starts,
- connection banner is clear when API is reachable.

## 2) Preflight Gates

Stop the sweep immediately if any gate fails.

### Gate A: Static checks

- `dotnet test frontend/TwitchClipper.Frontend.sln`
- `pytest tests/backend/test_api_jobs.py -q`

### Gate B: Runtime API checks

- `GET /health` must be `200`.
- `GET /jobs?limit=1` must be `200`.
- `POST /jobs/vod-highlights` with happy path URL must return `job_id`.
- `POST /jobs/clip-montage` with one known streamer must return `job_id`.

### Gate C: Determinism check for invalid URL oracle

Run:

```powershell
python scripts/frontend_bug_sweep.py
```

Expected:

- all strict URL oracle cases pass,
- script exit code is `0`.

## 3) Fixed Inputs

### Happy path URL

- `https://www.twitch.tv/videos/2713566602`

### Invalid URL set

- malformed: `not-a-url`
- non-video twitch: `https://www.twitch.tv/somechannel`
- guarded host: `https://invalid.invalid/videos/2713566602`
- empty boundary: `""`

## 4) Strict Oracle

These are exact checks for unattended auto-classification.

### Case `empty-url`

- input: `""`
- PASS when UI validation includes exact text:
  - `VOD URL is required.`
- and submit is blocked (`CanSubmit == false`).

### Case `malformed-url`

- input: `not-a-url`
- PASS when:
  - submit endpoint returns `200` with `job_id`,
  - after `POST /jobs/run-next`, job status is `failed`,
  - exact job error:
    - `Invalid input string: not-a-url`

### Case `non-video-twitch-url`

- input: `https://www.twitch.tv/somechannel`
- PASS when final failed error equals:
  - `Invalid input string: https://www.twitch.tv/somechannel`

### Case `unreachable-host-guarded`

- input: `https://invalid.invalid/videos/2713566602`
- PASS when final failed error equals:
  - `Invalid input string: https://invalid.invalid/videos/2713566602`

### Companion network-path oracle

- precondition: API process offline.
- PASS when form alert is exactly:
  - `Network error while submitting VOD job.`

## 5) Desktop Automation Strategy (WPF)

Use FlaUI + UIA3 for desktop behavior emulation.

- why: native WPF support and stable automation id lookups.
- test target: built desktop binary from this repo.
- scope:
  - happy flow actions,
  - failure flow actions,
  - edge flow actions,
  - bounded stress loops for navigation and refresh.

Execution model:

1. Start API.
2. Launch desktop app process.
3. Drive UI by automation ids.
4. Assert visible state transitions and messages.
5. Save machine-readable defects.

Scenario definitions are stored in:

- `frontend/automation/bug_sweep_scenarios.json`

## 6) Scenario Charter (Top 10)

1. startup hydration + online banner
2. offline startup banner and degraded mode
3. vod submit success with fixed URL
4. clip montage submit success
5. malformed VOD URL failure oracle
6. non-video Twitch URL failure oracle
7. guarded unreachable host failure oracle
8. queue refresh failure + recovery
9. job detail load + stale 404
10. rerun prefill + sparse params

## 7) Defect Schema and Severity

Use schema file:

- `frontend/automation/defect_report_schema.json`

Severity:

- `S1`: crash, data loss, blocker
- `S2`: core flow broken, no workaround
- `S3`: degraded behavior, workaround exists
- `S4`: cosmetic, low risk

Required defect fields:

- `id`
- `scenario`
- `severity`
- `preconditions`
- `steps`
- `expected`
- `actual`
- `artifacts`
- `suspected_area`

## 8) Fast Commands

Run strict API oracle:

```powershell
python scripts/frontend_bug_sweep.py
```

Run frontend unit/integration tests:

```powershell
dotnet test frontend/TwitchClipper.Frontend.sln
```

Run backend API job tests:

```powershell
pytest tests/backend/test_api_jobs.py -q
```
