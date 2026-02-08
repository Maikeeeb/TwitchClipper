# Template setup guide (for first agent)

Use this document to guide the first agent through turning the template into a
project-specific repo. The agent should ask the user for missing details and
update the referenced files directly.

## 0) Confirm the repo was created from the template

Expected command:
```bash
gh repo create TwitchClipper --template Not used --clone
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

Replace all placeholder tokens in:

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

- `TwitchClipper` <project display name>
- `Python` <e.g., Python, TypeScript>
- `None (uses Selenium + MoviePy)` <e.g., FastAPI, React, None>
- `CLI: python cli/main.py; API: uvicorn api.main:app --reload; UI: Not implemented yet (npm run dev)` <CLI/API/UI entry commands>
- `python cli/main.py` <CLI entry command or module path>
- `uvicorn api.main:app --reload` <API start command>
- `Not implemented yet (npm run dev)` <frontend dev server command>
- `Not used` <tutorial or examples command>
- `Not used` <config file paths>
- `Not used` <config helper module paths>
- `Not used` <data folder paths>
- `Not used` <schema file paths>
- `backend/` <backend root folder>
- `Not used` <backend config module paths>
- `backend/clips.py`, `backend/oneVideo.py`, `backend/transition.py`, `backend/overlay.py` <domain logic module paths>
- `api/` <backend API module paths>
- `cli/main.py`, `cli/upload.py`, `cli/testing.py`, `cli/test.py` <backend CLI module paths>
- `backend` <backend packages for coverage targets>
- `api/` <API root folder>
- `uvicorn api.main:app --reload` <API entry modules/commands>
- `/health` <route list or router modules>
- `Not used` <CORS/auth/limits references>
- `frontend/` (planned) <frontend root folder>
- `Not implemented yet` <frontend app entry file>
- `Not used` <shared types/utils paths>
- `Not used` <frontend test folder>
- `Not used` <test utils paths>
- `Not used` <test command(s)>
- `Not used` <MCP demo test paths>
- `Not used` <MCP demo command(s)>
- `Not used` <run all tests command>
- `Not used` <coverage command>
- `Not used` <watch mode command>
- `Not used` <coverage output paths>
- `Not used` <coverage summary path>
- `Python 3.10+, Selenium, MoviePy, natsort, Pillow, pywin32, Firefox + geckodriver` <tool names and versions>
  - `geckodriver.exe` should be on your PATH or placed in `backend/` (used by `backend/clips.py`)
  - Optional env var: `GECKODRIVER_PATH` to override the driver location
  - First-time setup script: `python scripts/setup_selenium.py`
- `selenium`, `moviepy`, `natsort`, `Pillow`, `pywin32` <production dependencies>
- `Not used` <test dependencies>
- `Not used` <lint/format dependencies>
- `Not used` <pre-commit dependencies>
- `Not used` <type stubs>
- `python -m pip install -r requirements.txt` <install/deps/initialize commands>
- `python cli/main.py` <run/start commands>
- `pytest --cov` <test commands>
  - Integration tests: set `RUN_TWITCH_INTEGRATION=1` and optionally `TWITCH_STREAMER`
- `Not used` <deploy commands>
- `Not used` <Low/Medium/High>
- `Not used` <Free/Low/Medium/High>
- `Not used` <use cases>
- `Not used` <Low/Medium/High>
- `Not used` <Free/Low/Medium/High>
- `Not used` <use cases>
- `Not used` <Low/Medium/High>
- `Not used` <Free/Low/Medium/High>
- `Not used` <use cases>
- `Not used` <Low/Medium/High>
- `Not used` <Free/Low/Medium/High>
- `Not used` <use cases>
- `Not used` <build commands>
- `uvicorn api.main:app --reload` <start command>
- `Not used` <hosting providers>
- `Not used` <backend build commands>
- `uvicorn api.main:app --reload` <backend start command>
- `Not used` <backend hosting providers>
- `Not used` <backend env var names>
- `Not implemented yet (npm run build)` <frontend build commands>
- `Not used` <frontend output dir>
- `Not used` <frontend hosting providers>
- `Not used` <frontend env var names>
- `Not used` <base image name>
- `Not used` <docker build command>
- `Not used` <docker run command>
- `Not used` <backend env vars with descriptions>
- `Not used` <frontend env vars with descriptions>
- `Not used` <env vars for unified deploy>
- `Not used` <healthcheck URL>
- `Not used` <production URL>
- `Not used` <smoke test command>

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
