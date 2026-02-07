# Deployment Quickstart (Template)

Use this quickstart for the simplest deployment path. Replace placeholders with
your real commands and provider.

## Option A: Single-service deployment

1. Build:
   ```bash
   {{UNIFIED_BUILD_COMMANDS}} <build commands>
   ```
2. Start:
   ```bash
   {{UNIFIED_START_COMMAND}} <start command>
   ```
3. Configure environment variables:
   - `{{UNIFIED_ENV_VARS}}` <env var names>
4. Verify health check:
   - `{{HEALTHCHECK_URL}}` <healthcheck URL>

## Option B: Separate frontend + backend

### Backend

1. Build:
   ```bash
   {{BACKEND_BUILD_COMMANDS}} <backend build commands>
   ```
2. Start:
   ```bash
   {{BACKEND_START_COMMAND}} <backend start command>
   ```
3. Configure environment variables:
   - `{{BACKEND_ENV_VARS}}` <backend env var names>

### Frontend

1. Build:
   ```bash
   {{FRONTEND_BUILD_COMMANDS}} <frontend build commands>
   ```
2. Publish directory: `{{FRONTEND_PUBLISH_DIR}}` <output dir>
3. Configure environment variables:
   - `{{FRONTEND_ENV_VARS}}` <frontend env var names>

## Validation

- Confirm production URL: `{{PROD_URL}}` <production URL>
- Smoke test command: `{{SMOKE_TEST_COMMAND}}` <smoke test command>
