# Frontend Troubleshooting

## API unreachable
- Symptom: top banner shows "Connection unavailable".
- Check API is running: `uvicorn api.main:app --reload`.
- Verify `Frontend:ApiBaseUrl` in `frontend/TwitchClipper.Desktop/appsettings.json`.

## Invalid form values (422)
- Symptom: submit shows validation errors.
- Fix required fields and numeric ranges in SCR-002 / SCR-003.
- Retry submit after correcting highlighted inputs.

## Job not found (404)
- Symptom: detail view shows "Job not found".
- Cause: stale row or removed job id.
- Action: return to queue and refresh.

## Output path open fails
- Symptom: "output path does not exist" message.
- Confirm output file/folder exists on disk.
- If running with DB disabled, outputs may be unavailable until job completion artifacts are persisted.

## Run next hidden
- Symptom: no "Run next" button in queue.
- Confirm `DeveloperMode` is `true` in frontend app settings profile.
