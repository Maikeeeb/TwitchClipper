# Repository overview and developer guide

This document is the hub for repo structure, entry points, and pointers to key files.

## Repository map (folders only)

```
Project Template/ - Repository root (rename as needed for your project)
├── .github/ - GitHub settings and automation
│   └── workflows/ - CI workflows and checks (e.g., tests, lint)
├── agents/ - Agent role definitions and domain guidance
├── docs/ - Project documentation templates and guides
└── workflows/ - Multi-agent workflow templates
    └── contexts/ - Workflow handoff artifacts
```

## Data files and schemas

- **Primary data** lives in `{{DATA_PATHS}}` <data directories>
- **Schemas** live in `{{SCHEMA_PATHS}}` <schema paths>
- **Configuration schema** mirrors the runtime config model and drives validation for API/UI inputs

## Backend layout (`{{BACKEND_ROOT}}` <backend root folder>)

- **Configuration**: `{{BACKEND_CONFIG_PATHS}}` <config modules>
- **Domain logic**: `{{BACKEND_DOMAIN_PATHS}}` <core logic modules>
- **Public API**: `{{BACKEND_API_PATHS}}` <backend API modules>
- **CLI entrypoint**: `{{BACKEND_CLI_PATHS}}` <CLI modules or scripts>

## API service (`{{API_ROOT}}` <API root folder>)

- Entry points: `{{API_ENTRY_POINTS}}` <startup modules/commands>
- Routes: `{{API_ROUTES}}` <route modules or list>
- CORS/auth/limits: `{{API_CROSS_CUTTING}}` <cross-cutting concerns>

## Frontend (`{{FRONTEND_ROOT}}` <frontend root folder>)

- App entry: `{{FRONTEND_ENTRY}}` <main entry file>
- Shared types/utils: `{{FRONTEND_SHARED_PATHS}}` <shared modules>
- Testing: `{{FRONTEND_TEST_PATHS}}` <test folders>

## Pointers (start here to find things fast)

- `README.md` - Project overview, run commands, and onboarding
- `AGENTS.md` - Coding standards and agent guidance
- `docs/TEMPLATE.md` - Template philosophy and required customizations
- `docs/setup.md` - First-agent setup checklist and placeholder list
- `docs/audit.md` - Placeholder audit tracking
- `docs/architecture.md` - Architecture template (data flow, boundaries, invariants)
- `docs/glossary.md` - Domain terminology quick reference
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
