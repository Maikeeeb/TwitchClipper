# Workflow System

This directory contains workflow definitions for multi-agent tasks. Workflows coordinate multiple specialized agents to complete complex features that span multiple domains.

## What Are Workflows?

Workflows are structured plans that define:
- **Objective**: What feature or task is being built
- **Agent Order**: Which agents run and in what sequence
- **Pass Rules**: How many iterations (max passes) and domain constraints
- **Completion Criteria**: When the workflow is considered done
- **Handoff Rules**: How agents communicate via shared context

## When to Use Workflows

**Use workflows when:**
- Task requires multiple agents (e.g., API + Frontend + Testing)
- Feature spans multiple domains (backend + frontend)
- Complex feature that needs coordination
- Task requires bounded iteration (multiple passes)

**Use single agents when:**
- Task is clearly within one domain
- Simple, focused change
- Single agent can complete the task

## Workflow Lifecycle

1. **Planner Agent** analyzes prompt and detects multi-agent task
2. **Planner Agent** creates workflow definition file in `workflows/`
3. **Planner Agent** creates handoff artifact in `workflows/contexts/`
4. **Agents execute** in defined order, appending to context file
5. **Pass 1** completes with all agents
6. **Pass 2** (if needed) runs same agents (Planner does NOT rerun)
7. **Completion criteria** checked
8. **Context file** archived or deleted after merge

## Bounded Iteration

Workflows use **bounded iteration** to prevent infinite loops:

- **Max passes**: Default 2 (configurable per workflow)
- **Planner runs once**: Scope is frozen after first pass
- **Fixed agent order**: Agents rotate in the same sequence
- **Explicit stopping**: Completion criteria must be met

## Handoff Artifacts

Each workflow has a corresponding handoff artifact in `workflows/contexts/`:

- **One context per workflow**: `workflows/contexts/<feature-name>.md`
- **Append-only**: Agents add to their section, never overwrite
- **Status tracking**: IN PROGRESS, COMPLETE, BLOCKED
- **Pending items**: Explicit list of remaining work
- **Versioned**: Stored in repo with code
- **Ephemeral**: Deleted or archived after merge

See [`contexts/README.md`](contexts/README.md) for detailed handoff artifact documentation.

## Creating Workflows

### Automatic Creation (Recommended)

The Planner Agent automatically creates workflows when it detects multi-agent tasks:

```
User: "Add a new Reports page with filtering and data display"
Planner: Creates workflows/add-reports-page.md and workflows/contexts/reports-page.md
```

### Manual Creation

1. Copy `_template.md` to create new workflow
2. Fill in objective, agent order, pass rules, completion criteria
3. Use descriptive filename: `add-<feature-name>.md`
4. Planner Agent will create corresponding context file

## Workflow Template Structure

See [`_template.md`](_template.md) for the complete template structure.

Key sections:
- **Objective**: Clear description of what's being built
- **Agent Order**: Numbered list of agents in execution order
- **Pass Rules**: Max passes, domain constraints, stopping conditions
- **Completion Criteria**: Specific, testable conditions
- **Handoff Rules**: How agents communicate

## Example Workflows

- [`add-feature-page.md`](add-feature-page.md) - Example of adding a new page feature

## Best Practices

1. **Keep workflows focused**: One workflow = one feature
2. **Define clear completion criteria**: Avoid ambiguity
3. **Set appropriate max passes**: Default 2, increase only if needed
4. **Use descriptive names**: `add-<feature>.md` format
5. **Clean up contexts**: Archive or delete after merge
6. **Respect agent boundaries**: Each agent only modifies their domain

## Guardrails

- **Max passes enforced**: Prevents infinite loops
- **Domain boundaries**: Agents cannot edit outside their domain
- **Append-only contexts**: Prevents context corruption
- **Planner frozen scope**: Planner does not rerun after first pass
- **Completion required**: Workflow must meet completion criteria

## Integration with Agents

All agents must:
- Read workflow definition when provided
- Read handoff artifact for context
- Append to their section only
- List pending items explicitly
- Respect domain boundaries
- Follow pass rules

See individual agent files in [`../agents/`](../agents/) for agent-specific guidelines.
