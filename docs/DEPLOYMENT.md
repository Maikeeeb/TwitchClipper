# Deployment Guide (Template)

Use this file to document how your project is deployed. Replace placeholders
with your real stack details.

## Quick decision matrix

| Option | Complexity | Cost | Best For |
|--------|-----------|------|----------|
| **Unified deployment** | Not used | Not used | Not used |
| **Platform-as-a-Service** | Not used | Not used | Not used |
| **Separate deployments** | Not used | Not used | Not used |
| **Docker / Containers** | Not used | Not used | Not used |

---

## Option 1: Unified deployment

Describe the unified approach (single service, same runtime).

- Build steps: `Not used`
- Start command: `uvicorn api.main:app --reload`
- Hosting options: `Not used`

---

## Option 2: Separate deployments

Describe independent frontend/backend deployments.

### Backend

- Build steps: `Not used`
- Start command: `uvicorn api.main:app --reload`
- Hosting options: `Not used`
- Required environment variables: `Not used`

### Frontend

- Build steps: `Not implemented yet (npm run build)`
- Publish directory: `Not used`
- Hosting options: `Not used`
- Required environment variables: `Not used`

---

## Option 3: Containers

Document containerization strategy if used.

- Base image: `Not used`
- Build command: `Not used`
- Run command: `Not used`

---

## Environment variables

### Backend

`Not used`

### Frontend

`Not used`

---

## Deployment checklist

- [ ] Services build successfully
- [ ] Services are reachable in production
- [ ] Environment variables configured
- [ ] CORS/auth configured (if applicable)
- [ ] Monitoring/logging configured
- [ ] Custom domain/HTTPS configured (if applicable)
