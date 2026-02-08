---
# TwitchClipper

Download Twitch clips from a streamer list, name them with streamer and views,
then compile into a montage.

## What this template provides

- Coding standards and agent guidance in `AGENTS.md`
- Pre-commit configuration in `.pre-commit-config.yaml`
- CI pipeline in `.github/workflows/ci.yml`
- Workflow and context templates in `workflows/`
- Project documentation templates in `docs/`

## Quick start

1. Create a new repo from this template:
   ```bash
   gh repo create TwitchClipper --template Not used --clone
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

- **Primary language:** `Python`
- **Primary framework:** `None (uses Selenium + MoviePy; API planned with FastAPI)`
- **Entry points:** `CLI: python cli/main.py; API: uvicorn api.main:app --reload; UI: Not implemented yet (npm run dev)`
- **Configuration files:** `Not used`

## Development

### Prerequisites

- `Python 3.10+, Selenium, MoviePy, natsort, Pillow, pywin32, Firefox + geckodriver`
- `geckodriver.exe` should be on your PATH or placed in `backend/` (the scripts look for it there)
- Optional: set `GECKODRIVER_PATH` to a custom driver path

### Local setup

```bash
python -m pip install -r requirements.txt
```

### Selenium setup (first-time)

Download a compatible geckodriver into `backend/`:
```bash
python scripts/setup_selenium.py
```

### Run locally

```bash
python cli/main.py
uvicorn api.main:app --reload
```

## Testing

```bash
pytest --cov
```

Integration tests that hit twitch.tv are skipped by default. To enable (PowerShell):
```bash
$env:RUN_TWITCH_INTEGRATION=1
$env:TWITCH_STREAMER="zubatlel"
```

## Deployment

```bash
Not used
```

## Docs

Primary hub: `docs/repo_overview.md` (repo structure, entry points, pointers).

- `docs/glossary.md` - Domain terminology quick reference

- `docs/repo_overview.md` - Codebase layout and runtime flow
- `docs/DEPLOYMENT.md` - Deployment notes and patterns
- `docs/DEPLOYMENT_QUICKSTART.md` - Quickstart for deployment

## Project-specific agents

Define backend/domain agent guidance in `agents/backend-solver-agent.md`.
