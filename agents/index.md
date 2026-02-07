# Available Agents

This directory contains reusable agent role definitions for AI-assisted development. Each agent has specific responsibilities, constraints, and domain knowledge.

## Default Agent: Planner Agent

**The [Planner Agent](planner-agent.md) is the default entry point for all prompts.** It analyzes incoming prompts, determines which specialized agents are needed, and coordinates their execution. If no specific agent is mentioned, the Planner Agent will automatically route the task to the appropriate agent(s).

## Quick Reference

| Agent | Focus Area | Key Responsibilities |
|-------|------------|---------------------|
| **[Planner Agent](planner-agent.md)** | **Prompt analysis & coordination** | **Analyzes prompts, routes to agents, coordinates execution** |
| [Backend Solver Agent](backend-solver-agent.md) | Backend/domain logic | {{DOMAIN_NAME}} <domain name> algorithms, search, scoring |
| [Frontend UI Agent](frontend-ui-agent.md) | React/TypeScript UI | Components, Material-UI, user interactions |
| [API Agent](api-agent.md) | FastAPI endpoints | REST API, validation, error handling |
| [Testing Agent](testing-agent.md) | Test automation | pytest, Vitest, test coverage |
| [Data Agent](data-agent.md) | Data management | Data files, schemas, validation |

## Usage Pattern

**Default (Recommended):** Let the Planner Agent analyze and route:
```
Improve spacing and responsiveness for the FilterPanel component.
```
The Planner Agent will automatically identify this needs the Frontend UI Agent.

**Explicit Agent Selection:** When you know which agent to use:
```
Use the Frontend UI Agent defined in agents/frontend-ui-agent.md.
Improve spacing and responsiveness for the FilterPanel component.
Do not touch logic.
```

**Complex Tasks:** The Planner Agent will coordinate multiple agents:
```
Add a new API endpoint to get champion stats and display them in the UI.
```
The Planner Agent will chain: API Agent → Frontend UI Agent → Testing Agent

## Agent Responsibilities

### Backend Solver Agent
- {{DOMAIN_NAME}} <domain name> algorithm implementation
- Search and optimization
- Scoring functions and tradeoffs
- Deterministic algorithm guarantees

### Frontend UI Agent
- React component development
- TypeScript type safety
- Material-UI theming and components
- User interaction patterns
- Accessibility standards

### API Agent
- FastAPI endpoint design
- Request/response validation
- Error handling and logging
- Rate limiting and CORS
- API versioning

### Testing Agent
- Backend testing with pytest
- Frontend testing with Vitest/React Testing Library
- Test coverage maintenance (90% minimum)
- Integration testing
- Test data and fixtures

### Data Agent
- Data file management (`{{DATA_PATHS}}` <data folders>)
- Schema validation (`{{SCHEMA_PATHS}}` <schema folders>)
- Data consistency and integrity
- Domain data parsing
- Configuration data validation

## Global Rules

All agents must follow the global rules defined in [`AGENTS.md`](../AGENTS.md), including:

- Scope and exceptions/overrides
- Non-goals
- Intent clarity
- Architecture constraints
- Coding conventions
- Pre-commit requirements
- Documentation guidelines
- Change discipline

## Agent Boundaries

Agents have clear boundaries to prevent conflicts:

- **Planner Agent** does not execute tasks directly - only coordinates and delegates
- **Backend Solver Agent** does not modify UI or API code
- **Frontend UI Agent** does not modify solver logic or Python code
- **API Agent** does not modify solver logic or frontend components
- **Testing Agent** does not modify production code unless fixing bugs
- **Data Agent** does not modify solver logic or UI code

## Adding New Agents

When adding a new agent role:

1. Create a new file: `agents/<role-name>-agent.md`
2. Follow the template structure (Responsibilities, Constraints, Quality Bar, Domain-Specific Rules)
3. Update this index file
4. Ensure the agent follows global rules from `AGENTS.md`

## Agent Chaining

Agents can be chained for complex tasks:

1. **UI Agent** → Layout and visual hierarchy
2. **Component Agent** → Props cleanup and boundaries
3. **Testing Agent** → Test coverage and edge cases

Each agent does one thing well and leaves the code cleaner for the next.

## Multi-Agent Workflows

For complex features requiring multiple agents with bounded iteration, use the **workflow system**:

- **Workflow definitions**: `workflows/` directory
- **Handoff artifacts**: `workflows/contexts/` directory
- **Bounded iteration**: Max 2 passes by default
- **Shared context**: Append-only handoff artifacts

See [`../workflows/README.md`](../workflows/README.md) for complete workflow documentation.

**When to use workflows:**
- Feature requires 3+ agents
- Task spans multiple domains (backend + frontend + testing)
- Complex feature needing coordination
- Task requires multiple passes

**When to use single agents:**
- Simple, focused change
- Task clearly within one domain
- Single agent can complete the task
