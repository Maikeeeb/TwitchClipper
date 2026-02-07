# Workflow: Add Feature Page

## Objective

Add a new feature page to the application that displays data with filtering, sorting, and basic interactions. This workflow demonstrates the complete multi-agent coordination pattern.

## Agent Order

1. **Planner Agent** - Creates workflow and context, defines scope, components, and routes
2. **API Agent** - Creates necessary API endpoints for data fetching
3. **Frontend UI Agent** - Creates page component, layout, and user interactions
4. **Testing Agent** - Adds comprehensive tests for API and UI components

## Pass Rules

- **Max passes**: 2
- **Planner Agent**: Runs once in Pass 1 only (frozen scope)
- **Other agents**: Rotate in fixed order: API Agent → Frontend UI Agent → Testing Agent
- **Domain constraints**: 
  - API Agent may ONLY modify `ui_api/main.py` and related API code
  - Frontend UI Agent may ONLY modify `frontend/src/components/` and related UI code
  - Testing Agent may ONLY modify test files in `tests/` or `frontend/src/__tests__/`
- **Stopping condition**: Workflow completes when:
  - All completion criteria are met, OR
  - Max passes (2) reached

## Completion Criteria

- [ ] API endpoint(s) created and functional
- [ ] Page component renders without errors
- [ ] Filtering functionality works correctly
- [ ] Data displays correctly
- [ ] No console errors or warnings
- [ ] Tests pass with 90%+ coverage
- [ ] No TODOs or FIXMEs left in code
- [ ] Accessibility basics met (keyboard nav, ARIA labels)

## Handoff Rules

Each agent must:

1. **Read the handoff artifact**: `workflows/contexts/<feature-name>.md`
2. **Implement their domain**: Only modify files in their responsibility
3. **Append to their section**: Add results, notes, and pending items
4. **Never overwrite**: Do not modify other agents' sections
5. **List pending items**: Explicitly state what remains for next agent or next pass
6. **Update status**: Mark their section as complete or note blockers

## Notes

This is an example workflow demonstrating the pattern. When creating actual workflows, replace with specific feature requirements.
