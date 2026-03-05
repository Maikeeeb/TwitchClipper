# Front-End TODOs for Completing `ui-spec.md`

Use this checklist to fully populate `docs/ui-spec.md` before implementation.

## Status Guide
- [ ] Not started
- [~] In progress
- [x] Done

## Phase 1: Scope and Product Intent
- [ ] UI-SPEC-001 Define project metadata in `ui-spec.md` (owner, status, links, scope).
- [ ] UI-SPEC-002 Fill Goals section with measurable outcomes.
- [ ] UI-SPEC-003 Fill Non-Goals section to prevent scope creep.
- [ ] UI-SPEC-004 Identify primary users and top 3 use cases.
- [ ] UI-SPEC-005 Add at least 2 user stories.

## Phase 2: Structure and Navigation
- [ ] UI-SPEC-006 Build a complete screen inventory table with IDs and transitions.
- [ ] UI-SPEC-007 Decide navigation model (single-window panes, tabs, wizard, etc.).
- [ ] UI-SPEC-008 Define back/cancel rules and any deep-link behavior.

## Phase 3: Flows and Diagrams
- [ ] UI-SPEC-009 Replace placeholder flowchart with real happy-path flow.
- [ ] UI-SPEC-010 Document alternate flows (invalid input, failed processing, retry).
- [ ] UI-SPEC-011 Update state diagram for actual app states.
- [ ] UI-SPEC-012 Add a key sequence diagram for the primary user action.
- [ ] UI-SPEC-013 Draft initial UI-layer class diagram (view models/services only).

## Phase 4: Per-Screen Details
- [ ] UI-SPEC-014 Create one "Screen Specifications" block for each screen in inventory.
- [ ] UI-SPEC-015 Define component tables (IDs, behavior, validation) for each screen.
- [ ] UI-SPEC-016 Define actions and outcomes tables for each screen.
- [ ] UI-SPEC-017 Define empty/loading/error states for each screen.
- [ ] UI-SPEC-018 Add resize/window behavior notes for each screen.

## Phase 5: UX and Accessibility
- [ ] UI-SPEC-019 Define all input validation rules (required, ranges, formats).
- [ ] UI-SPEC-020 Define success/error/progress feedback behavior.
- [ ] UI-SPEC-021 Define keyboard navigation and shortcuts.
- [ ] UI-SPEC-022 Complete accessibility checklist (focus, contrast, labels).

## Phase 6: Data and Integration
- [ ] UI-SPEC-023 List view models and their properties/commands.
- [ ] UI-SPEC-024 Fill data contract table with DTOs/models used by UI.
- [ ] UI-SPEC-025 Fill backend integration table (action, request, response, error behavior).
- [ ] UI-SPEC-026 Define offline/no-network behavior and messaging.

## Phase 7: Visual Foundation
- [ ] UI-SPEC-027 Fill initial design token choices (font, color roles, spacing).
- [ ] UI-SPEC-028 Note any desktop constraints (minimum window size, DPI scaling).

## Phase 8: Completion and Review
- [ ] UI-SPEC-029 Fill acceptance criteria and verify each checkbox has evidence in the doc.
- [ ] UI-SPEC-030 Fill open questions with owner + due date per question.
- [ ] UI-SPEC-031 Add at least one risk with mitigation.
- [ ] UI-SPEC-032 Add initial change log entry.
- [ ] UI-SPEC-033 Run a final review for consistency between screen inventory, flows, and diagrams.

## Recommended Working Order
1. UI-SPEC-001 to UI-SPEC-008
2. UI-SPEC-009 to UI-SPEC-013
3. UI-SPEC-014 to UI-SPEC-018
4. UI-SPEC-019 to UI-SPEC-026
5. UI-SPEC-027 to UI-SPEC-033

## Definition of Done
- [ ] Every placeholder in `docs/ui-spec.md` is replaced with concrete content.
- [ ] All diagram placeholders are replaced with project-specific diagrams.
- [ ] All screen IDs and component IDs are consistent across the document.
- [ ] Acceptance criteria are all checked and justified.
