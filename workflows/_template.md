# Workflow: [Feature Name]

## Objective

[Clear description of what feature or task is being built. Be specific about scope and requirements.]

Example:
Add a new Reports page that displays filtered report data with sorting and export capabilities.

## Agent Order

1. [Planner Agent] - Creates workflow and context, defines scope
2. [Agent Name] - [What this agent does]
3. [Agent Name] - [What this agent does]
4. [Agent Name] - [What this agent does]

Example:
1. Planner Agent - Creates workflow, defines components and routes
2. API Agent - Creates GET /reports endpoint with filtering
3. Frontend UI Agent - Creates ReportsPage component with filters and table
4. Testing Agent - Adds tests for API endpoint and UI component

## Pass Rules

- **Max passes**: 2 (default)
- **Planner Agent**: Runs once in Pass 1 only (frozen scope)
- **Other agents**: Rotate in fixed order for each pass
- **Domain constraints**: Each agent may ONLY modify files in their responsibility domain
- **Stopping condition**: Workflow completes when:
  - All completion criteria are met, OR
  - Max passes reached (even if criteria not fully met)

## Completion Criteria

[Specific, testable conditions that must be met for workflow completion.]

Example:
- [ ] Page renders without errors at `/reports`
- [ ] Filtering works correctly (by date, status, type)
- [ ] Data displays in table format
- [ ] Export functionality works
- [ ] No console errors
- [ ] Tests pass with 90%+ coverage
- [ ] No TODOs or FIXMEs left in code

## Handoff Rules

Each agent must:

1. **Read the handoff artifact**: `workflows/contexts/<feature-name>.md`
2. **Implement their domain**: Only modify files in their responsibility
3. **Append to their section**: Add results, notes, and pending items
4. **Never overwrite**: Do not modify other agents' sections
5. **List pending items**: Explicitly state what remains for next agent or next pass
6. **Update status**: Mark their section as complete or note blockers

## Notes

[Any additional context, constraints, or considerations for this workflow.]
