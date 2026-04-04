# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tech Stack

- **Backend:** FastAPI + Beanie ODM (v2.x) + MongoDB + Motor (async driver) + Celery + Redis + Playwright
- **Testing:** Pytest + anyio + httpx (AsyncClient + ASGITransport)
- **Frontend:** React 19 + TypeScript + Vite + TanStack Router + TanStack Query + Tailwind CSS v4 + shadcn/ui
- **Package managers:** `uv` (Python), `pnpm` (JS)
- **Infrastructure:** Docker Compose + Traefik reverse proxy

## Development Environment

This project uses **Docker-based development** — all operations run inside containers. You only need Docker and Make installed locally.

### Prerequisites

- Docker (with Compose v2.22+)
- Make

No need to install Python, Node.js, uv, or pnpm locally!

### Quick Start

```bash
make dev    # Start development environment with hot reload
```

Services available at:
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- Flower (Celery): http://localhost:5555

### Makefile Commands

```bash
make help                 # Show all available commands

# Development
make up                   # Start all services (detached)
make dev                  # Start with live-reload (recommended)
make down                 # Stop and remove containers
make logs                 # Show logs from all services

# Testing (all run inside containers)
make test                 # Run all tests
make test-backend         # Backend tests
make test-frontend        # Frontend E2E tests

# Code Quality
make lint                 # Run all linters
make format               # Format all code
make check                # Run all checks (lint + test)

# Code Generation
make generate-client      # Generate OpenAPI client (backend -> frontend)

# Shell Access
make shell-backend        # Open shell in backend container
make shell-frontend       # Open shell in frontend container

# Package Management
make add-backend PACKAGE=requests       # Add Python package
make add-frontend PACKAGE=lodash        # Add npm package
```

See [DOCKER_DEV.md](DOCKER_DEV.md) for complete documentation.

### Legacy: Local Development (Not Recommended)

If you must run locally without Docker:

**Backend** (from `backend/`):
```bash
uv run fastapi dev app/main.py
uv run pytest tests/
bash scripts/lint.sh
```

**Frontend** (from `frontend/`):
```bash
pnpm install
pnpm run dev
pnpm run lint
```

## Architecture

### Backend

- **Entry:** `backend/app/main.py` — creates FastAPI app with lifespan (calls `init_db`), CORS middleware, mounts all routes under `/api/v1`
- **Routes:** `backend/app/api/main.py` aggregates route modules including `users`, `items`, `sources`, `articles`, `submit`, `analyses`, `agents`, `workflows`, `drafts`, `skills`, `tools`, `task_runs`, `rubrics`, `external_references`, `token_usage`, `system_config`
- **Auth:** fastapi-users v15 (JWT). `backend/app/core/users.py` provides `current_active_user`, `current_superuser` dependencies
- **Models:** `backend/app/models/` — Beanie `Document` classes with UUID PKs; see `models/__init__.py` for full list
- **Config:** `backend/app/core/config.py` — Pydantic `BaseSettings` loaded from top-level `.env`
- **DB:** `backend/app/core/db.py` — `init_db()` creates `AsyncIOMotorClient`, calls `init_beanie()` with all models, seeds first superuser

### Content Intelligence Engine (Core Domain)

The application is a content intelligence platform with the following key components:

#### Article Lifecycle
1. **Ingestion** (`submit.py`, `fetch.py`)
   - Manual text submission
   - URL fetching (HTTP + Playwright fallback with LLM quality validation)
   - RSS/API source fetching
2. **Refinement** (`refiner.py`, `refine.py`)
   - Content cleaning and structuring
   - Markdown conversion
3. **Analysis** (`react_analyzer.py`, `analyze.py`)
   - ReAct-based AI analysis with tool calling
   - Quality scoring via rubrics (5 dimensions: content_depth, readability, originality, ai_flavor, virality_potential)
   - AI flavor detection (high score = natural human writing, low score = AI-generated)
   - External reference enrichment

#### Agent System (`core/agents/`)
- **BaseAgent** (`base.py`): Core agent loop with tool dispatch, context compression, token usage tracking
- **Specialized Agents**: RefinerAgent, ReactAnalyzerAgent, WriterAgent, EditorAgent, ReviewerAgent, OrchestratorAgent
- **FetcherAgent** (`fetcher.py`): Intelligent content fetching with HTTP/Playwright/LLM validation
- **AgentConfig** (`models/agent_config.py`): Database-driven agent configuration (role, model, tools, skills)

#### Task System (`tasks/`)
Celery tasks for async processing:
- `fetch_source_task`: Batch fetch from RSS/API sources
- `fetch_url_and_analyze_task`: Manual URL submission
- `refetch_article_task`: Re-fetch existing article
- `refine_article_task`: Content refinement
- `analyze_article_task`: AI analysis
- `rewrite_section_task`: Content rewriting

#### Workflow System (`workflows.py`, `workflow.py`)
- Multi-step agent workflows with human-in-the-loop approval
- SSE streaming for real-time updates
- Support for approve/reject/retry operations

### Frontend

- **File-based routing** via TanStack Router; `src/routeTree.gen.ts` is auto-generated — do not edit manually
- **API calls** use the auto-generated client in `src/client/` via TanStack Query hooks
- **Auth routes** (`login.tsx`, `signup.tsx`, etc.) are at the top level; authenticated pages live under `src/routes/_layout/`
- **UI components** follow shadcn/ui pattern in `src/components/`
- **Forms** use react-hook-form + Zod validation
- **System Settings** (`UserSettings/SystemSettings.tsx`): Configure word cloud filters (excluded keywords, max count) and API keys

### Key Models

| Model | Purpose |
|-------|---------|
| `User` | Authentication via fastapi-users |
| `Article` | Content articles (raw → refined → analyzed) |
| `Source` | RSS/API subscription sources |
| `AgentConfig` | AI agent configurations |
| `WorkflowRun` | Multi-step workflow executions |
| `Draft` | Editable content drafts |
| `Skill` | Reusable agent capabilities |
| `Tool` | External tool definitions |
| `TaskRun` | Task execution tracking |
| `QualityRubric` | Analysis scoring criteria (content_depth, readability, originality, ai_flavor, virality_potential) |
| `ExternalReference` | Reference materials for analysis |
| `InsightSnapshot` | Pre-aggregated knowledge base analytics with word clouds and distributions |
| `SystemConfig` | System-wide configuration including word cloud filters and LLM provider settings |
| `TokenUsage` | LLM token usage tracking |
| `InsightSnapshot` | Pre-aggregated knowledge base analytics |

### Deployment (Docker)

**Production deployment:**
```bash
docker compose build backend
docker compose build frontend
docker compose up -d
```

**Development deployment (with hot reload):**
```bash
make build
make dev
```

**Verify deployment:**
```bash
docker compose ps
curl -s http://localhost:8000/api/v1/utils/health-check/
curl -s http://localhost:5173/ > /dev/null && echo "Frontend OK"
```

**Deployment checklist:**
- [ ] Backend health check returns `true`
- [ ] Frontend serves index.html
- [ ] All containers show `Up` status
- [ ] Celery beat and worker running

### Database

MongoDB with Beanie ODM. No migrations needed — Beanie manages indexes automatically on startup via `init_beanie()`.

**Async testing pattern:** all tests are `async def` (auto-run via `anyio_mode = "auto"`). Use `httpx.AsyncClient(transport=ASGITransport(app=app))` — never `TestClient`, which creates a separate event loop incompatible with Beanie/Motor. The `db` fixture (session-scoped) calls `init_db()` once and cleans up with `delete_all()` after the session.

### Environment configuration

Copy `.env` template and set at minimum: `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD` before deploying. Backend reads config exclusively from the top-level `.env` file via Pydantic settings.

## Key Ports (dev)

| Service | Port |
|---|---|
| Backend API | 8000 |
| Frontend | 5173 |
| MongoDB | 27017 |
| Redis | 6379 |
| Traefik dashboard | 8090 |
| Mailcatcher (web) | 1080 |

## Key File Locations

| Purpose | Path |
|---------|------|
| Models | `backend/app/models/` |
| API Routes | `backend/app/api/routes/` |
| Agents | `backend/app/core/agents/` |
| Tasks | `backend/app/tasks/` |
| Tools | `backend/app/core/tools/` |
| LLM Clients | `backend/app/core/llm/` |
| Frontend Routes | `frontend/src/routes/` |
| Frontend Components | `frontend/src/components/` |
| Generated Client | `frontend/src/client/` |
