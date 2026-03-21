# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tech Stack

- **Backend:** FastAPI + Beanie ODM (v2.x) + MongoDB + Motor (async driver) + PyJWT + pwdlib (argon2 + bcrypt)
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
- **Routes:** `backend/app/api/main.py` aggregates route modules: `login`, `users`, `items`, `utils`, `private` (local-only)
- **Auth:** JWT (PyJWT). `backend/app/api/deps.py` provides `CurrentUser`, `TokenDep`, and `get_current_active_superuser` dependencies
- **Models:** `backend/app/models.py` — Beanie `Document` classes for `User` and `Item` with UUID PKs; Pydantic `BaseModel` for all request/response schemas
- **CRUD:** `backend/app/crud.py` — async thin layer over Beanie queries
- **Config:** `backend/app/core/config.py` — Pydantic `BaseSettings` loaded from top-level `.env`
- **DB:** `backend/app/core/db.py` — `init_db()` creates `AsyncIOMotorClient`, calls `init_beanie([User, Item])`, seeds first superuser, returns client (closed by lifespan on shutdown)
- **Prestart:** `backend/scripts/prestart.sh` runs `backend_pre_start.py` (MongoDB ping with retry) then `initial_data.py` (calls `init_db()` to seed superuser)

### Frontend

- **File-based routing** via TanStack Router; `src/routeTree.gen.ts` is auto-generated — do not edit manually
- **API calls** use the auto-generated client in `src/client/` via TanStack Query hooks
- **Auth routes** (`login.tsx`, `signup.tsx`, etc.) are at the top level; authenticated pages live under `src/routes/_layout/`
- **UI components** follow shadcn/ui pattern in `src/components/`
- **Forms** use react-hook-form + Zod validation

### Database

MongoDB with Beanie ODM. No migrations needed — Beanie manages indexes automatically on startup via `init_beanie()`. Collections: `users`, `items`.

**Password hashing:** argon2 (via pwdlib) is the default. Legacy bcrypt hashes are automatically upgraded to argon2 on next login (`crud.authenticate` handles this transparently).

**Async testing pattern:** all tests are `async def` (auto-run via `anyio_mode = "auto"`). Use `httpx.AsyncClient(transport=ASGITransport(app=app))` — never `TestClient`, which creates a separate event loop incompatible with Beanie/Motor. The `db` fixture (session-scoped) calls `init_db()` once and cleans up with `delete_all()` after the session.

### Environment configuration

Copy `.env` template and set at minimum: `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD` before deploying. Backend reads config exclusively from the top-level `.env` file via Pydantic settings.

## Key Ports (dev)

| Service | Port |
|---|---|
| Backend API | 8000 |
| Frontend | 5173 |
| MongoDB | 27017 |
| Traefik dashboard | 8090 |
| Mailcatcher (web) | 1080 |
