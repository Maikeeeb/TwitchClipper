# Template setup guide (for first agent)

Use this document to guide the first agent through turning the template into a
project-specific repo. The agent should ask the user for missing details and
update the referenced files directly.

## 0) Confirm the repo was created from the template

Expected command:
```bash
gh repo create {{NEW_REPO_NAME}} <new-repo-name> --template {{TEMPLATE_REPO}} <owner/template-repo> --clone
```

## 1) Gather project profile (ask the user)

Capture these values before editing files:

- Project name and short description
- Primary language and framework(s)
- Entry points (CLI/API/UI) and how to run locally
- Config/data/schema locations
- Test strategy and commands
- Deployment target and commands
- Tooling expectations (lint/format/type-check)

## 2) Fill placeholders in core docs

Replace all `{{...}}` placeholders in:

- @README.md
- @AGENTS.md
- @requirements.txt
- @requirements-dev.txt
- @docs/repo_overview.md
- @docs/DEPLOYMENT.md
- @docs/DEPLOYMENT_QUICKSTART.md
- @docs/architecture.md
- @docs/audit.md

Reference docs:

- @docs/TEMPLATE.md

Common placeholders you must resolve:

- `{{PROJECT_NAME}}` <project display name>
- `{{PRIMARY_LANGUAGE}}` <e.g., Python, TypeScript>
- `{{PRIMARY_FRAMEWORK}}` <e.g., FastAPI, React, None>
- `{{ENTRY_POINTS}}` <CLI/API/UI entry commands>
- `{{CLI_ENTRY_POINT}}` <CLI entry command or module path>
- `{{API_ENTRY_POINT}}` <API start command>
- `{{FRONTEND_ENTRY_POINT}}` <frontend dev server command>
- `{{TUTORIAL_ENTRY_POINT}}` <tutorial or examples command>
- `{{CONFIG_PATHS}}` <config file paths>
- `{{CONFIG_HELPER_PATHS}}` <config helper module paths>
- `{{DATA_PATHS}}` <data folder paths>
- `{{SCHEMA_PATHS}}` <schema file paths>
- `{{BACKEND_ROOT}}` <backend root folder>
- `{{BACKEND_CONFIG_PATHS}}` <backend config module paths>
- `{{BACKEND_DOMAIN_PATHS}}` <domain logic module paths>
- `{{BACKEND_API_PATHS}}` <backend API module paths>
- `{{BACKEND_CLI_PATHS}}` <backend CLI module paths>
- `{{BACKEND_PACKAGES}}` <backend packages for coverage targets>
- `{{API_ROOT}}` <API root folder>
- `{{API_ENTRY_POINTS}}` <API entry modules/commands>
- `{{API_ROUTES}}` <route list or router modules>
- `{{API_CROSS_CUTTING}}` <CORS/auth/limits references>
- `{{FRONTEND_ROOT}}` <frontend root folder>
- `{{FRONTEND_ENTRY}}` <frontend app entry file>
- `{{FRONTEND_SHARED_PATHS}}` <shared types/utils paths>
- `{{FRONTEND_TEST_PATHS}}` <frontend test folder>
- `{{FRONTEND_TEST_UTILS_PATHS}}` <test utils paths>
- `{{FRONTEND_TEST_COMMANDS}}` <test command(s)>
- `{{FRONTEND_MCP_TEST_PATHS}}` <MCP demo test paths>
- `{{FRONTEND_MCP_TEST_COMMANDS}}` <MCP demo command(s)>
- `{{FRONTEND_TEST_ALL_COMMAND}}` <run all tests command>
- `{{FRONTEND_TEST_COVERAGE_COMMAND}}` <coverage command>
- `{{FRONTEND_TEST_WATCH_COMMAND}}` <watch mode command>
- `{{FRONTEND_COVERAGE_PATHS}}` <coverage output paths>
- `{{FRONTEND_COVERAGE_SUMMARY_PATH}}` <coverage summary path>
- `{{REQUIRED_TOOLS}}` <tool names and versions>
- `{{PROD_DEPENDENCIES}}` <production dependencies>
- `{{TEST_DEPENDENCIES}}` <test dependencies>
- `{{LINT_DEPENDENCIES}}` <lint/format dependencies>
- `{{PRECOMMIT_DEPENDENCIES}}` <pre-commit dependencies>
- `{{TYPE_STUB_DEPENDENCIES}}` <type stubs>
- `{{SETUP_COMMANDS}}` <install/deps/initialize commands>
- `{{RUN_COMMANDS}}` <run/start commands>
- `{{TEST_COMMANDS}}` <test commands>
- `{{DEPLOY_COMMANDS}}` <deploy commands>
- `{{UNIFIED_COMPLEXITY}}` <Low/Medium/High>
- `{{UNIFIED_COST}}` <Free/Low/Medium/High>
- `{{UNIFIED_BEST_FOR}}` <use cases>
- `{{PAAS_COMPLEXITY}}` <Low/Medium/High>
- `{{PAAS_COST}}` <Free/Low/Medium/High>
- `{{PAAS_BEST_FOR}}` <use cases>
- `{{SEPARATE_COMPLEXITY}}` <Low/Medium/High>
- `{{SEPARATE_COST}}` <Free/Low/Medium/High>
- `{{SEPARATE_BEST_FOR}}` <use cases>
- `{{DOCKER_COMPLEXITY}}` <Low/Medium/High>
- `{{DOCKER_COST}}` <Free/Low/Medium/High>
- `{{DOCKER_BEST_FOR}}` <use cases>
- `{{UNIFIED_BUILD_COMMANDS}}` <build commands>
- `{{UNIFIED_START_COMMAND}}` <start command>
- `{{UNIFIED_HOSTS}}` <hosting providers>
- `{{BACKEND_BUILD_COMMANDS}}` <backend build commands>
- `{{BACKEND_START_COMMAND}}` <backend start command>
- `{{BACKEND_HOSTS}}` <backend hosting providers>
- `{{BACKEND_ENV_VARS}}` <backend env var names>
- `{{FRONTEND_BUILD_COMMANDS}}` <frontend build commands>
- `{{FRONTEND_PUBLISH_DIR}}` <frontend output dir>
- `{{FRONTEND_HOSTS}}` <frontend hosting providers>
- `{{FRONTEND_ENV_VARS}}` <frontend env var names>
- `{{DOCKER_BASE_IMAGE}}` <base image name>
- `{{DOCKER_BUILD_COMMAND}}` <docker build command>
- `{{DOCKER_RUN_COMMAND}}` <docker run command>
- `{{BACKEND_ENV_VAR_LIST}}` <backend env vars with descriptions>
- `{{FRONTEND_ENV_VAR_LIST}}` <frontend env vars with descriptions>
- `{{UNIFIED_ENV_VARS}}` <env vars for unified deploy>
- `{{HEALTHCHECK_URL}}` <healthcheck URL>
- `{{PROD_URL}}` <production URL>
- `{{SMOKE_TEST_COMMAND}}` <smoke test command>

If a section does not apply to the project, remove it or mark it "Not used".

## 2.1) Minimal stack variants (quick keep/delete guide)

Use one of these variants to prune the template quickly.

### Backend-only

- Keep: `agents/backend-solver-agent.md`, backend tests, backend CI job
- Remove or mark Not used: frontend sections in README/AGENTS, frontend CI job
- Update: `docs/repo_overview.md` to remove frontend pointers

### Frontend-only

- Keep: `agents/frontend-ui-agent.md`, frontend tests, frontend CI job
- Remove or mark Not used: backend/API sections in README/AGENTS, backend CI job
- Update: `docs/repo_overview.md` to remove backend/API pointers

### Full-stack

- Keep: both backend and frontend sections, both CI jobs
- Update: repo overview with both sides and shared boundaries

## 3) Update agent guidance

- Adjust @agents/backend-solver-agent.md to reflect your real backend/domain
  responsibilities and constraints.
- Remove any irrelevant sections from @AGENTS.md (for example, frontend or API
  guidance if the project is backend-only).
- Update placeholders in:
  - @agents/planner-agent.md
  - @agents/index.md
  - @agents/backend-solver-agent.md
  - @agents/frontend-ui-agent.md
  - @agents/api-agent.md
  - @agents/testing-agent.md
  - @agents/data-agent.md

## 4) Align tooling and CI

- Update @.pre-commit-config.yaml to match the stack.
- Update @.github/workflows/ci.yml to run the correct tests and checks.
- Update @requirements.txt / @requirements-dev.txt or add @package.json
  as needed.
- Update @.gitignore for any new build artifacts or tool outputs.

## 5) Establish repo structure

- Create or rename top-level folders (e.g., `src/`, `backend/`, `frontend/`).
- Ensure @docs/repo_overview.md reflects the final structure.
- Add a minimal example module or entry point if the project is greenfield.

## 6) Validate and hand off

- Confirm README, docs, and agent guidance are consistent.
- Run lint/format/tests once if available.
- Summarize any remaining TODOs for the next agent or developer.

## 7) Repo health checklist (short)

- README matches actual run/test/deploy commands
- CI is green and running the correct jobs
- Lint/format/type-check are configured and pass
- Tests pass locally at least once
- Docs reflect current structure and entry points
