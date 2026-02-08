# Repository overview and developer guide

This document is the hub for repo structure, entry points, and pointers to key files.

## Repository map (folders only)

```
TwitchClipper/ - Repository root
├── .github/ - GitHub settings and automation
│   └── workflows/ - CI workflows and checks (e.g., tests, lint)
├── agents/ - Agent role definitions and domain guidance
├── api/ - FastAPI service
├── backend/ - Backend logic (clip download/processing)
├── cli/ - CLI entry points
├── docs/ - Project documentation templates and guides
├── tests/ - Pytest suites
└── workflows/ - Multi-agent workflow templates
    └── contexts/ - Workflow handoff artifacts
```

## Data files and schemas

- **Primary data** lives in `Not used`
- **Schemas** live in `Not used`
- **Configuration schema** mirrors the runtime config model and drives validation for API/UI inputs

## Backend layout (`backend/`)

- **Configuration**: `Not used`
- **Domain logic**: `backend/clips.py`, `backend/oneVideo.py`, `backend/transition.py`,
  `backend/overlay.py`
- **Public API**: `Not implemented yet`
- **CLI entrypoint**: `cli/main.py`

## API service (`api/`)

- Entry points: `uvicorn api.main:app --reload`
- Routes: `/health`
- CORS/auth/limits: `Not used`

## Frontend (`frontend/` planned)

- App entry: `Not implemented yet (planned React entry)`
- Shared types/utils: `Not used`
- Testing: `Not used`

## Pointers (start here to find things fast)

- `README.md` - Project overview, run commands, and onboarding
- `AGENTS.md` - Coding standards and agent guidance
- `docs/TEMPLATE.md` - Template philosophy and required customizations
- `docs/setup.md` - First-agent setup checklist and placeholder list
- `docs/audit.md` - Placeholder audit tracking
- `docs/architecture.md` - Architecture template (data flow, boundaries, invariants)
- `docs/backend_report.md` - Backend behavior report and risks
- `docs/glossary.md` - Domain terminology quick reference
- `docs/TODO.md` - Prioritized backend fixes and features
- `CONTRIBUTING.md` - PR checklist and standards
- `.pre-commit-config.yaml` - Formatting and lint hooks
- `.editorconfig` - Whitespace and line ending rules
- `.github/workflows/ci.yml` - CI pipeline and test commands
- `docs/DEPLOYMENT.md` - Deployment strategy and decision matrix
- `docs/DEPLOYMENT_QUICKSTART.md` - Quick deployment steps
- `LICENSE` - License selection placeholder
- `agents/index.md` - Agent role index
- `workflows/README.md` - Workflow system overview
- `workflows/contexts/README.md` - Handoff artifact format
