# Desktop Automation Harness (WPF)

This folder defines the unattended desktop behavior sweep contract.

## Strategy

- Framework: FlaUI (`UIA3`) for native WPF automation.
- Target: `frontend/TwitchClipper.Desktop` running against local API.
- Input source: scenario manifest in `frontend/automation/scenarios/bug_sweep_scenarios.json`.
- Output: defect objects that conform to
  `frontend/automation/defect_report_schema.json`.

## Runner Responsibilities

1. Start/verify API connectivity.
2. Launch desktop executable.
3. Resolve controls by automation id first, then stable fallback selectors.
4. Execute scenarios in order:
   - happy
   - failure
   - edge
5. Capture artifacts for failed assertions:
   - screenshot path
   - logs path
   - optional API payload snapshot
6. Emit defect records using strict oracle rules where provided.

## Determinism Rules

- Do not use random test inputs.
- Use fixed URL fixtures from scenario files.
- Use bounded retries with explicit timeout values.
- Fail fast if API health is unavailable.

## Suggested Invocation Contract

Any harness implementation should accept:

- `--api-base-url` (default `http://127.0.0.1:8000`)
- `--scenario-file` (default this folder's scenario JSON)
- `--results-file` (output defects/results JSON)
- `--screenshots-dir` (artifact folder)

## Notes

- This repository currently provides the scenario and schema contract.
- The runtime harness can be implemented in C# (xUnit + FlaUI) or Python
  (pywinauto) as a follow-up, as long as it honors this contract.
