# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tech Stack

- **Backend:** FastAPI + Beanie ODM (v2.x) + MongoDB + Motor (async driver) + Celery + Redis + Playwright
- **Testing:** Pytest + anyio + httpx (AsyncClient + ASGITransport)
- **Frontend:** React 19 + TypeScript + Vite + TanStack Router + TanStack Query + Tailwind CSS v4 + shadcn/ui
- **Package managers:** `uv` (Python), `pnpm` (JS)
- **Infrastructure:** Docker Compose + Traefik reverse proxy

## Development Commands

### Start the dev stack

```bash
docker compose watch    # with live-reload file sync
# or
docker compose up -d
```

### Backend (run from `backend/` using `uv run`)

```bash
uv run fastapi dev app/main.py          # dev server (without Docker)
uv run pytest tests/                    # all tests
uv run pytest tests/api/routes/test_users.py                    # single file
uv run pytest tests/api/routes/test_users.py::test_name -v     # single test
bash scripts/lint.sh                    # mypy + ruff check + ruff format --check
bash scripts/format.sh                  # ruff format
```

Via running Docker container:
```bash
docker compose exec backend bash scripts/tests-start.sh        # all tests
docker compose exec backend bash scripts/tests-start.sh -- -x  # stop on first failure
```

### Frontend (run from `frontend/` or repo root)

```bash
pnpm install
pnpm run dev              # Vite dev server
pnpm run build            # tsc + vite build
pnpm run lint             # Biome check with autofix
pnpm exec playwright test     # all E2E tests
pnpm exec playwright test tests/login.spec.ts   # single test file
pnpm exec playwright test --ui                  # interactive UI mode
```

### Generate OpenAPI client (after backend changes)

```bash
bash scripts/generate-client.sh   # from repo root
# or
pnpm run generate-client           # from frontend/
```

The generated client lives in `frontend/src/client/` — do not edit it manually.

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

**Build and deploy all services:**
```bash
docker compose build --no-cache backend
docker compose build --no-cache frontend
docker compose up -d
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
