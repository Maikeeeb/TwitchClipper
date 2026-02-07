---
# {{PROJECT_NAME}} <project display name>

Short description of the project goes here.

## What this template provides

- Coding standards and agent guidance in `AGENTS.md`
- Pre-commit configuration in `.pre-commit-config.yaml`
- CI pipeline in `.github/workflows/ci.yml`
- Workflow and context templates in `workflows/`
- Project documentation templates in `docs/`

## Quick start

1. Create a new repo from this template:
   ```bash
   gh repo create {{NEW_REPO_NAME}} <new-repo-name> --template {{TEMPLATE_REPO}} <owner/template-repo> --clone
   ```
2. Follow the checklist in `docs/setup.md` to replace placeholders and configure the repo.

## Agent onboarding

Start with `docs/setup.md` to guide the first agent through template setup and
project-specific configuration.

## Template references

- `docs/TEMPLATE.md` - Template philosophy and required customizations
- `docs/architecture.md` - Architecture template (data flow, boundaries, invariants)
- `docs/audit.md` - Placeholder audit tracking

## Project overview

- **Primary language:** `{{PRIMARY_LANGUAGE}}` <e.g., Python, TypeScript>
- **Primary framework:** `{{PRIMARY_FRAMEWORK}}` <e.g., FastAPI, React, None>
- **Entry points:** `{{ENTRY_POINTS}}` <CLI/API/UI commands or scripts>
- **Configuration files:** `{{CONFIG_PATHS}}` <paths like config.json, .env>

## Development

### Prerequisites

- `{{REQUIRED_TOOLS}}` <tool names and versions, e.g., Python 3.12, Node 20>

### Local setup

```bash
{{SETUP_COMMANDS}} <commands to install deps and initialize environment>
```

### Run locally

```bash
{{RUN_COMMANDS}} <commands to start the app locally>
```

## Testing

```bash
{{TEST_COMMANDS}} <commands to run tests>
```

## Deployment

```bash
{{DEPLOY_COMMANDS}} <commands or scripts used to deploy>
```

## Docs

Primary hub: `docs/repo_overview.md` (repo structure, entry points, pointers).

- `docs/glossary.md` - Domain terminology quick reference

- `docs/repo_overview.md` - Codebase layout and runtime flow
- `docs/DEPLOYMENT.md` - Deployment notes and patterns
- `docs/DEPLOYMENT_QUICKSTART.md` - Quickstart for deployment

## Project-specific agents

Define backend/domain agent guidance in `agents/backend-solver-agent.md`.
