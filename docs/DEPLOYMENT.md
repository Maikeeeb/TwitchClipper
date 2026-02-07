# Deployment Guide (Template)

Use this file to document how your project is deployed. Replace placeholders
with your real stack details.

## Quick decision matrix

| Option | Complexity | Cost | Best For |
|--------|-----------|------|----------|
| **Unified deployment** | {{UNIFIED_COMPLEXITY}} <Low/Medium/High> | {{UNIFIED_COST}} <Free/Low/Medium/High> | {{UNIFIED_BEST_FOR}} <use cases> |
| **Platform-as-a-Service** | {{PAAS_COMPLEXITY}} <Low/Medium/High> | {{PAAS_COST}} <Free/Low/Medium/High> | {{PAAS_BEST_FOR}} <use cases> |
| **Separate deployments** | {{SEPARATE_COMPLEXITY}} <Low/Medium/High> | {{SEPARATE_COST}} <Free/Low/Medium/High> | {{SEPARATE_BEST_FOR}} <use cases> |
| **Docker / Containers** | {{DOCKER_COMPLEXITY}} <Low/Medium/High> | {{DOCKER_COST}} <Free/Low/Medium/High> | {{DOCKER_BEST_FOR}} <use cases> |

---

## Option 1: Unified deployment

Describe the unified approach (single service, same runtime).

- Build steps: `{{UNIFIED_BUILD_COMMANDS}}` <build commands>
- Start command: `{{UNIFIED_START_COMMAND}}` <start command>
- Hosting options: `{{UNIFIED_HOSTS}}` <provider list>

---

## Option 2: Separate deployments

Describe independent frontend/backend deployments.

### Backend

- Build steps: `{{BACKEND_BUILD_COMMANDS}}` <backend build commands>
- Start command: `{{BACKEND_START_COMMAND}}` <backend start command>
- Hosting options: `{{BACKEND_HOSTS}}` <provider list>
- Required environment variables: `{{BACKEND_ENV_VARS}}` <env var names>

### Frontend

- Build steps: `{{FRONTEND_BUILD_COMMANDS}}` <frontend build commands>
- Publish directory: `{{FRONTEND_PUBLISH_DIR}}` <output dir>
- Hosting options: `{{FRONTEND_HOSTS}}` <provider list>
- Required environment variables: `{{FRONTEND_ENV_VARS}}` <env var names>

---

## Option 3: Containers

Document containerization strategy if used.

- Base image: `{{DOCKER_BASE_IMAGE}}` <e.g., python:3.12-slim>
- Build command: `{{DOCKER_BUILD_COMMAND}}` <docker build ...>
- Run command: `{{DOCKER_RUN_COMMAND}}` <docker run ...>

---

## Environment variables

### Backend

`{{BACKEND_ENV_VAR_LIST}}` <name=value pairs with descriptions>

### Frontend

`{{FRONTEND_ENV_VAR_LIST}}` <name=value pairs with descriptions>

---

## Deployment checklist

- [ ] Services build successfully
- [ ] Services are reachable in production
- [ ] Environment variables configured
- [ ] CORS/auth configured (if applicable)
- [ ] Monitoring/logging configured
- [ ] Custom domain/HTTPS configured (if applicable)
