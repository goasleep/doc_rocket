# Articles Page: Backend Search + URL State Sync Design

## Goal
Move article list filtering (status, source, title search) and pagination state to the backend and sync all state with the URL so that filters and pagination are shareable and survive page refreshes.

## Changes

### 1. Backend (`backend/app/api/routes/articles.py`)
- Add optional query parameter `search: str | None = None` to `GET /articles/`.
- When `search` is provided, apply a case-insensitive regex filter on `Article.title` using Beanie’s `Regex` operator.
- Keep existing `skip`/`limit`/`status`/`source_id` behavior unchanged.
- Return `ArticlesPublic` with `count` (total matching records) and `data` (current page).

### 2. Frontend URL state (`frontend/src/routes/_layout/articles/index.tsx`)
- Define TanStack Router search validators for:
  - `page` (number, default 1)
  - `status` (string, default "all")
  - `source` (string, default "all")
  - `search` (string, default "")
- All list parameters live in the URL query string (e.g. `?page=2&status=raw&source=manual&search=ai`).
- Changing any filter resets `page` to 1.

### 3. Frontend data fetching
- Update `useSuspenseQuery` so `queryKey` includes `page`, `status`, `source`, `search`.
- Pass those values as query params to `ArticlesService.listArticles()`.
- Remove local client-side filtering (`data.data.filter(...)`); use backend-returned data directly.
- Pagination component continues to use `data.count` and `pageSize = 10`.

### 4. UI/UX
- Keep existing shadcn/ui `Table`, `Pagination`, `Select`, `Input`, `Checkbox`, and bulk-delete toolbar.
- Search input, status select, and source select remain visually unchanged but now drive URL state.

## Out of scope
- Full-text search index (MongoDB regex is sufficient for current scale).
- Advanced sorting beyond existing `created_at` descending.
- Integration with a frontend table library like `@tanstack/react-table`.
