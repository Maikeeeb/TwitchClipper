# Handoff Artifacts

Handoff artifacts are shared context files that enable agents to coordinate on multi-agent workflows. They serve as a transaction log and shared state between agents.

## What Are Handoff Artifacts?

Handoff artifacts are markdown files in `workflows/contexts/` that:
- Store shared state between agents
- Track progress across agent passes
- List pending items explicitly
- Provide audit trail in version control
- Enable state continuity without memory hacks

## Structure

Each handoff artifact follows this structure:

```markdown
# Feature Context: [Feature Name]

## Status
IN PROGRESS | COMPLETE | BLOCKED

## Planner Output
- Route: /feature-name
- Components: [list]
- State: [requirements]
- API: [endpoints needed]

## [Agent Name] Agent
- [What was implemented]
- [Notes]
- Pending: [remaining items]

## Open Questions
- [Any unresolved questions]

## Pending Items
- [Explicit list of remaining work]
```

## Rules

### 1. One Context Per Workflow Instance

- ❌ **Don't reuse** contexts across features
- ✅ **Copy from template** for each new workflow
- ✅ **Use descriptive names**: `feature-name.md` (kebab-case)

### 2. Append-Only Per Agent

Agents must:
- ✅ **Add a section** with their agent name
- ✅ **Append to their section** only
- ❌ **Never rewrite** other agents' sections
- ❌ **Never delete** content from other sections

This prevents silent context corruption.

### 3. Explicit Pending Sections

Each agent must:
- ✅ **List pending items** explicitly
- ✅ **Mark blockers** clearly
- ✅ **Note dependencies** on other agents

This forces convergence and prevents infinite loops.

### 4. Status Management

Update status at the top:
- **IN PROGRESS**: Workflow is active
- **COMPLETE**: All criteria met, ready to merge
- **BLOCKED**: Cannot proceed (note blocker in Open Questions)

### 5. Delete or Archive After Merge

After feature merges to main:

```bash
# Option 1: Delete
git rm workflows/contexts/feature-name.md

# Option 2: Archive
mkdir -p workflows/contexts/archive
git mv workflows/contexts/feature-name.md workflows/contexts/archive/
```

Do not let contexts accumulate indefinitely.

## Usage Pattern

### For Agents

When an agent is invoked with a workflow:

```
Use the [Agent Name] Agent.

Read workflows/contexts/feature-name.md.
Implement only [domain]-related pending items.
Append your results to your section.
```

The agent should:
1. Read the context file
2. Find their section (or create it)
3. Implement pending items in their domain
4. Append results to their section
5. List any new pending items
6. Never modify other agents' sections

### For Planner Agent

The Planner Agent:
1. Creates context file from `_template.md`
2. Fills in Planner Output section
3. Sets status to IN PROGRESS
4. Delegates to first agent with context file reference

## Template

See [`_template.md`](_template.md) for the complete template structure.

## Benefits

### Version Control Integration

Because handoff artifacts are:
- **Text files**: Clear diffs
- **Scoped**: Easy to find
- **Append-only**: Simple conflict resolution
- **Versioned**: Full audit trail

You get:
- Clear history of agent actions
- Ability to rewind agent changes
- Easy conflict resolution
- Perfect for per-agent branches

### State Continuity

Handoff artifacts provide:
- **Deterministic state**: Same context = same behavior
- **No memory hacks**: State lives in files
- **Retry-safe**: Can restart from any point
- **Human-readable**: Progress visible to developers

## Advanced Pattern: Context Checkpoints

For very large features, you can use checkpointed contexts:

```
workflows/contexts/feature-name/
 ├── 00-planner.md
 ├── 01-components.md
 ├── 02-state.md
 ├── 03-ui.md
 └── 04-qa.md
```

Only use this pattern for features that span multiple days or have complex dependencies.

## What NOT To Do

| Mistake | Consequence |
|---------|-------------|
| Let agents overwrite context | Chaos, lost information |
| Store context in chat | Lost on retry, not versioned |
| Keep contexts forever | Repo bloat, confusion |
| Mix multiple features | Cross-contamination |
| Store context per agent | No shared truth |
| Skip pending items | Infinite loops, unclear progress |

## Examples

See existing context files in this directory for real examples (when workflows are active).
