# AGENTS.md

This file provides guidance for AI agents (Claude, Gemini, etc.) when working with this repository.

## Project Overview

A full-stack content intelligence platform with FastAPI backend and React frontend.

## Development Environment

**CRITICAL: This project uses Docker-based development exclusively.**

All development operations MUST run inside Docker containers. Do NOT execute commands directly on the host machine.

### Prerequisites

- Docker (with Compose v2.22+)
- Make

### Command Reference

Always use `make` commands instead of direct tool invocations:

| Task | Correct (Docker) | Incorrect (Local) |
|------|-----------------|-------------------|
| Start dev server | `make dev` | `uv run fastapi dev` or `pnpm run dev` |
| Run tests | `make test` | `uv run pytest` or `pnpm test` |
| Lint code | `make lint` | `bash scripts/lint.sh` or `pnpm lint` |
| Format code | `make format` | `bash scripts/format.sh` or `pnpm format` |
| Add backend package | `make add-backend PACKAGE=name` | `uv add name` |
| Add frontend package | `make add-frontend PACKAGE=name` | `pnpm add name` |
| Generate client | `make generate-client` | `bash scripts/generate-client.sh` |
| Shell access | `make shell-backend` | `cd backend` |

### Container Structure

```
┌─────────────────────────────────────────────────────────┐
│  Host Machine (only Docker + Make)                     │
└─────────────────────────────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌─────────┐        ┌─────────────┐        ┌──────────┐
│ backend │        │  frontend   │        │ mongodb  │
│ container│       │  container  │        │ container│
│         │        │             │        │          │
│ • Python│        │ • Node 22   │        │ • MongoDB│
│ • uv    │        │ • pnpm      │        │   7      │
│ • FastAPI│       │ • Vite      │        │          │
│ • Celery│        │ • React 19  │        │          │
└─────────┘        └─────────────┘        └──────────┘
    │                      │
    └──────────────────────┼──────────────────────┐
                           │                      │
                    ┌──────────┐           ┌──────────┐
                    │  redis   │           │  flower  │
                    │ container│           │ (celery  │
                    │          │           │  monitor)│
                    └──────────┘           └──────────┘
```

## Agent Guidelines

### DO

- ✅ Use `make` commands for all operations
- ✅ Use `docker compose exec` to run commands in containers
- ✅ Check `make help` for available commands
- ✅ Read [DOCKER_DEV.md](DOCKER_DEV.md) for detailed documentation
- ✅ Use named volumes for persistence (data survives container restarts)

### DON'T

- ❌ Install Python/Node.js packages directly on host
- ❌ Run `uv` or `pnpm` commands directly (unless via `make`)
- ❌ Modify files in `frontend/src/client/` (auto-generated)
- ❌ Edit `frontend/src/routeTree.gen.ts` (auto-generated)

### File Locations

| Purpose | Path |
|---------|------|
| Backend source | `backend/app/` |
| Frontend source | `frontend/src/` |
| Models | `backend/app/models/` |
| API routes | `backend/app/api/routes/` |
| Agents | `backend/app/core/agents/` |
| Tasks | `backend/app/tasks/` |
| Frontend routes | `frontend/src/routes/` |
| UI components | `frontend/src/components/` |
| Auto-generated client | `frontend/src/client/` |

## Tech Stack

- **Backend:** FastAPI + Beanie ODM (v2.x) + MongoDB + Motor + Celery + Redis + Playwright
- **Frontend:** React 19 + TypeScript + Vite + TanStack Router + TanStack Query + Tailwind CSS v4 + shadcn/ui
- **Package managers:** `uv` (Python), `pnpm` (JS)
- **Infrastructure:** Docker Compose + Traefik reverse proxy

## Testing

All tests run inside containers:

```bash
make test                 # All tests
make test-backend         # Backend only
make test-frontend        # Frontend E2E only
make test-backend-watch   # Watch mode
```

Use `httpx.AsyncClient(transport=ASGITransport(app=app))` — never `TestClient`.

## Code Generation

After modifying backend API:

```bash
make generate-client      # Regenerates frontend/src/client/
```

## Architecture Notes

- **Auth:** fastapi-users v15 (JWT)
- **Database:** MongoDB with Beanie ODM (no migrations needed)
- **Async:** All tests are `async def` (anyio auto mode)
- **Hot reload:** Both backend (FastAPI) and frontend (Vite) support it

## Environment Variables

Copy `.env.example` to `.env` and configure:
- `SECRET_KEY` — Application secret
- `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD` — Initial admin
- `MONGODB_URL` — Database connection
- `REDIS_URL` — Redis connection
