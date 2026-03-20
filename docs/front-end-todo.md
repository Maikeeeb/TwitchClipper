# Desktop UI TODOs for Completing `ui-spec.md`

Use this checklist to fully populate `docs/ui-spec.md` before implementation.

## Status Guide
- [ ] Not started
- [~] In progress
- [x] Done

## Phase 1: Scope and Product Intent
- [x] UI-SPEC-001 Define project metadata in `ui-spec.md` (owner, status, links, scope).
- [x] UI-SPEC-002 Fill Goals section with measurable outcomes.
- [x] UI-SPEC-003 Fill Non-Goals section to prevent scope creep.
- [x] UI-SPEC-004 Identify primary users and top 3 use cases.
- [x] UI-SPEC-005 Add at least 2 user stories.

## Phase 2: Structure and Navigation
- [x] UI-SPEC-006 Build a complete screen inventory table with IDs and transitions.
- [x] UI-SPEC-007 Decide navigation model (single-window panes, tabs, wizard, etc.).
- [x] UI-SPEC-008 Define back/cancel rules and any deep-link behavior.

## Phase 3: Flows and Diagrams
- [x] UI-SPEC-009 Replace placeholder flowchart with real happy-path flow.
- [x] UI-SPEC-010 Document alternate flows (invalid input, failed processing, retry).
- [x] UI-SPEC-011 Update state diagram for actual app states.
- [x] UI-SPEC-012 Add a key sequence diagram for the primary user action.
- [x] UI-SPEC-013 Draft initial UI-layer class diagram (view models/services only).

## Phase 4: Per-Screen Details
- [x] UI-SPEC-014 Create one "Screen Specifications" block for each screen in inventory.
- [x] UI-SPEC-015 Define component tables (IDs, behavior, validation) for each screen.
- [x] UI-SPEC-016 Define actions and outcomes tables for each screen.
- [x] UI-SPEC-017 Define empty/loading/error states for each screen.
- [x] UI-SPEC-018 Add resize/window behavior notes for each screen.

## Phase 5: UX and Accessibility
- [x] UI-SPEC-019 Define all input validation rules (required, ranges, formats).
- [x] UI-SPEC-020 Define success/error/progress feedback behavior.
- [x] UI-SPEC-021 Define keyboard navigation and shortcuts.
- [x] UI-SPEC-022 Complete accessibility checklist (focus, contrast, labels).

## Phase 6: Data and Integration
- [x] UI-SPEC-023 List view models and their properties/commands.
- [x] UI-SPEC-024 Fill data contract table with DTOs/models used by UI.
- [x] UI-SPEC-025 Fill backend integration table (action, request, response, error behavior).
- [x] UI-SPEC-026 Define offline/no-network behavior and messaging.

## Phase 7: Visual Foundation
- [x] UI-SPEC-027 Fill initial design token choices (font, color roles, spacing).
- [x] UI-SPEC-028 Note any desktop constraints (minimum window size, DPI scaling).

## Phase 8: Completion and Review
- [x] UI-SPEC-029 Fill acceptance criteria and verify each checkbox has evidence in the doc.
- [x] UI-SPEC-030 Fill open questions with owner + due date per question.
- [x] UI-SPEC-031 Add at least one risk with mitigation.
- [x] UI-SPEC-032 Add initial change log entry.
- [x] UI-SPEC-033 Run a final review for consistency between screen inventory, flows, and diagrams.

## Recommended Working Order
1. UI-SPEC-001 to UI-SPEC-008
2. UI-SPEC-009 to UI-SPEC-013
3. UI-SPEC-014 to UI-SPEC-018
4. UI-SPEC-019 to UI-SPEC-026
5. UI-SPEC-027 to UI-SPEC-033

## Definition of Done
- [x] Every placeholder in `docs/ui-spec.md` is replaced with concrete content.
- [x] All diagram placeholders are replaced with project-specific diagrams.
- [x] All screen IDs and component IDs are consistent across the document.
- [x] Acceptance criteria are all checked and justified.

## Implementation TODOs (WPF .NET 8)
Use this checklist to turn `docs/ui-spec.md` into a working desktop app from bootstrap to release-ready.

### Phase 0: Foundation and Workflow Setup
- [x] UI-IMPL-001 Create WPF .NET 8 solution and project naming convention.
- [x] UI-IMPL-002 Define folder structure (`Views`, `ViewModels`, `Services`, `Models`, `Commands`, `Styles`).
- [x] UI-IMPL-003 Add baseline app settings model (API base URL, dev-mode flag, polling defaults).
- [x] UI-IMPL-004 Add dependency injection/container wiring in app startup.
- [x] UI-IMPL-005 Decide and scaffold logging strategy (debug console + file logs for diagnostics).

### Phase 1: Core Architecture and Shell
- [x] UI-IMPL-006 Build App Shell window layout (navigation rail, header, main content region).
- [x] UI-IMPL-007 Implement `AppShellViewModel` with `CurrentScreen` and selected job state.
- [x] UI-IMPL-008 Create navigation service for SCR-001 to SCR-005 transitions.
- [x] UI-IMPL-009 Implement reusable `ICommand` infrastructure (`RelayCommand`, async command variant).
- [x] UI-IMPL-010 Add shared base view model (`INotifyPropertyChanged`, validation state support).

### Phase 2: API and DTO Layer
- [x] UI-IMPL-011 Create typed DTOs matching locked contracts in `docs/ui-spec.md`.
- [x] UI-IMPL-012 Implement API client methods for `/health`, `/jobs/vod-highlights`, `/jobs/clip-montage`, `/jobs/{job_id}`, `/jobs/run-next`.
- [x] UI-IMPL-013 Implement JSON serialization options and nullability handling rules.
- [x] UI-IMPL-014 Add centralized API error mapper (422, 404, 500, network timeout).
- [x] UI-IMPL-015 Add API response validation guards for union responses (`RunNextResponseDto`).

### Phase 3: SCR-001 Dashboard
- [x] UI-IMPL-016 Create SCR-001 view and quick-action cards.
- [x] UI-IMPL-017 Bind recent jobs preview and worker/health summary.
- [x] UI-IMPL-018 Implement startup hydration and initial health check.

### Phase 4: VOD Vertical Slice (First End-to-End Flow)
- [x] UI-IMPL-019 Create SCR-002 VOD form view and `VodHighlightsFormViewModel`.
- [x] UI-IMPL-020 Implement field validation and submit enable/disable behavior.
- [x] UI-IMPL-021 Implement VOD submit call (`POST /jobs/vod-highlights`) and success navigation.
- [x] UI-IMPL-022 Build SCR-004 queue view with table, filters, and search.
- [x] UI-IMPL-023 Implement queue polling and status updates at configured interval.
- [x] UI-IMPL-024 Build SCR-005 detail view with summary/parameters/outputs/error tabs.
- [x] UI-IMPL-025 Render result, outputs, and error sections with null-safe fallback text.

### Phase 5: Clip Montage Flow
- [x] UI-IMPL-026 Create SCR-003 clip montage form and `ClipMontageFormViewModel`.
- [x] UI-IMPL-027 Implement streamer list parsing, dedupe, and validation rules.
- [x] UI-IMPL-028 Implement clip montage submit call (`POST /jobs/clip-montage`) and success navigation.
- [x] UI-IMPL-029 Ensure queue and detail screens support both job types.

### Phase 6: Cross-Screen Behaviors and Productivity
- [x] UI-IMPL-030 Implement rerun-prefill from SCR-005 into SCR-002/SCR-003.
- [x] UI-IMPL-031 Implement cancel-with-dirty-form modal confirmation behavior.
- [x] UI-IMPL-032 Implement output-path open action with missing/inaccessible path fallback.
- [x] UI-IMPL-033 Add `Run next` button behind developer mode only.
- [x] UI-IMPL-034 Implement keyboard shortcuts (`Ctrl+1..4`, `Ctrl+Enter`, `Ctrl+R`, `Esc`, `Alt+Left`).

### Phase 7: Offline, Reliability, and Error UX
- [x] UI-IMPL-035 Implement global connection banner and reconnect handling.
- [x] UI-IMPL-036 Implement degraded polling mode with retry/backoff behavior.
- [x] UI-IMPL-037 Implement endpoint-specific error UX according to HTTP error matrix.
- [x] UI-IMPL-038 Add user-facing error copy for common path and validation failures.

### Phase 8: Accessibility and Visual System
- [x] UI-IMPL-039 Apply typography/color/spacing tokens from spec.
- [x] UI-IMPL-040 Verify visible focus states and tab order across screens.
- [x] UI-IMPL-041 Validate contrast targets and non-color-only status indicators.
- [x] UI-IMPL-042 Add screen-reader labels/automation properties for key controls.
- [x] UI-IMPL-043 Validate resize behavior at minimum window size and 100/125/150 percent DPI.

### Phase 9: Test Implementation
- [x] UI-IMPL-044 Add unit tests for view models (validation, command can-execute, state transitions).
- [x] UI-IMPL-045 Add API client tests for DTO parsing and error mapping.
- [x] UI-IMPL-046 Add integration-style UI tests for submit -> queue -> detail happy path.
- [x] UI-IMPL-047 Add defect tests for 422 validation, 404 missing job, offline mode, and rerun parsing failures.
- [x] UI-IMPL-048 Add keyboard navigation and shortcut behavior tests where practical.

### Phase 10: Packaging and Release Readiness
- [x] UI-IMPL-049 Define dev and production configuration profiles.
- [x] UI-IMPL-050 Add build/publish scripts for Windows desktop artifacts.
- [x] UI-IMPL-051 Validate first-run behavior and required runtime dependencies.
- [x] UI-IMPL-052 Perform final spec conformance pass against locked UI spec sections.
- [x] UI-IMPL-053 Update `README.md` with desktop UI run/build instructions.
- [x] UI-IMPL-054 Add troubleshooting notes (API unreachable, invalid paths, failed jobs, dev-mode controls).
- Scope note: desktop run/build/troubleshooting instructions are documented in `docs/repo_overview.md` and `docs/frontend_troubleshooting.md` for this implementation pass.

### Definition of Done for Implementation
- [x] All SCR-001 to SCR-005 screens implemented and navigable.
- [x] Both submit flows (`vod_highlights`, `clip_montage`) work end-to-end against API.
- [x] Error handling, offline behavior, and rerun semantics match `docs/ui-spec.md`.
- [x] Keyboard and accessibility requirements are verified.
- [x] Packaging and run instructions are documented and reproducible.
