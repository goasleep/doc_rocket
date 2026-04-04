# Articles Search + URL State Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend title search to the articles list endpoint and sync pagination/filter state with the URL on the `/articles` page.

**Architecture:** Backend adds an optional `search` query parameter using MongoDB case-insensitive regex. Frontend replaces local React state with TanStack Router validated search params and passes all filters directly to `ArticlesService.listArticles()`.

**Tech Stack:** FastAPI + Beanie ODM, React 19 + TanStack Router/Query + shadcn/ui

---

## File Map

- **`backend/app/api/routes/articles.py`** — modify `list_articles()` to accept `search` and apply `Regex` filter on `Article.title`.
- **`backend/tests/api/routes/test_articles.py`** — add test for `search` query behavior.
- **`frontend/src/routes/_layout/articles/index.tsx`** — replace local `useState` with URL search params, update `useSuspenseQuery` to pass filters to the backend, remove client-side filtering.
- **`frontend/src/client/`** (auto-generated) — will be regenerated after backend OpenAPI changes.

---

### Task 1: Backend title search query parameter

**Files:**
- Modify: `backend/app/api/routes/articles.py`
- Test: `backend/tests/api/routes/test_articles.py`

- [ ] **Step 1: Add `search` to `list_articles` signature and apply regex filter**

In `backend/app/api/routes/articles.py`, update `list_articles`:

```python
@router.get("/", response_model=ArticlesPublic)
async def list_articles(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    source_id: uuid.UUID | None = None,
    input_type: str | None = None,
    sort: str = "created_at",
    search: str | None = None,
) -> Any:
    import asyncio
    from beanie.operators import Regex

    filters: list[Any] = [Article.status != "archived"]
    if status:
        filters = [Article.status == status]
    if source_id:
        filters.append(Article.source_id == source_id)
    if input_type:
        filters.append(Article.input_type == input_type)
    if search:
        filters.append(Regex(Article.title, search, options="i"))

    query = Article.find(*filters)

    count, articles = await asyncio.gather(
        query.count(),
        query.sort("-created_at").skip(skip).limit(limit).to_list(),
    )
    ...  # rest unchanged
```

- [ ] **Step 2: Add backend test for search query**

Add to `backend/tests/api/routes/test_articles.py`:

```python
@pytest.mark.anyio
async def test_list_articles_search(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
    article1 = Article(title="FastAPI tutorial", content="c1")
    article2 = Article(title="React patterns", content="c2")
    await article1.insert()
    await article2.insert()

    response = await client.get(
        "/api/v1/articles/?search=fastapi",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["title"] == "FastAPI tutorial"
```

- [ ] **Step 3: Run backend tests**

Run:
```bash
cd backend && MONGODB_URL=mongodb://localhost:27018 MONGODB_DB=test_fastapi_app uv run pytest tests/api/routes/test_articles.py -v
```
Expected: all tests pass.

- [ ] **Step 4: Commit backend changes**

```bash
git add backend/app/api/routes/articles.py backend/tests/api/routes/test_articles.py
git commit -m "feat: add search query to articles list endpoint with tests"
```

---

### Task 2: Regenerate frontend OpenAPI client

**Files:**
- Modify: `frontend/src/client/*` (auto-generated)

- [ ] **Step 1: Regenerate client**

Run from repo root:
```bash
bash scripts/generate-client.sh
```

- [ ] **Step 2: Verify `search` appears in generated types**

Check `frontend/src/client/types.gen.ts` for `ArticlesListArticlesData` to confirm it includes `search?: (string | null);`.

- [ ] **Step 3: Commit regenerated client**

```bash
git add frontend/src/client/
git commit -m "chore: regenerate client for articles search query"
```

---

### Task 3: Sync URL state and use backend filtering in frontend

**Files:**
- Modify: `frontend/src/routes/_layout/articles/index.tsx`

- [ ] **Step 1: Add zod search schema and use URL params**

At the top of the route file, after imports, add:

```typescript
const searchSchema = z.object({
  page: z.number().catch(1),
  status: z.string().catch("all"),
  source: z.string().catch("all"),
  search: z.string().catch(""),
})
```

Update `Route` definition:

```typescript
export const Route = createFileRoute("/_layout/articles/")({
  component: Articles,
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "文章库 - 内容引擎" }],
  }),
})
```

- [ ] **Step 2: Replace local state with URL-derived values in `ArticlesTableContent`**

Inside `ArticlesTableContent`, replace:

```typescript
const { page, status, source, search } = useSearch({ from: "/_layout/articles/" })
const navigate = useNavigate({ from: "/_layout/articles/" })
```

Remove the old `useState` declarations for `search`, `filterStatus`, `filterSource`, `page`. Keep `selected` as `useState` (selection is ephemeral).

Add a helper to update search params and reset page:

```typescript
const navigate = useNavigate({ from: "/_layout/articles/" })

function updateFilters(updates: Partial<typeof searchSchema._type>) {
  navigate({
    search: (prev) => ({ ...prev, ...updates, page: 1 }),
    replace: true,
  })
}
```

- [ ] **Step 3: Update `useSuspenseQuery` to pass all filters**

Replace the existing query with:

```typescript
const pageSize = 10
const { data } = useSuspenseQuery({
  queryKey: ["articles", page, status, source, search],
  queryFn: () =>
    ArticlesService.listArticles({
      skip: (page - 1) * pageSize,
      limit: pageSize,
      status: status === "all" ? null : status,
      sourceId: source === "all" || source === "manual" ? null : source,
      inputType: source === "manual" ? "manual" : null,
      search: search || null,
    }),
})
```

- [ ] **Step 4: Remove client-side filtering and update UI bindings**

Remove the `filtered` variable and all `.filter(...)` logic. Use `data.data` directly in the table.

Update filter controls:

```tsx
<Input
  placeholder="搜索标题..."
  value={search}
  onChange={(e) => updateFilters({ search: e.target.value })}
  className="h-8 w-56"
/>
<Select
  value={status}
  onValueChange={(v) => updateFilters({ status: v })}
>
  ...
</Select>
<Select
  value={source}
  onValueChange={(v) => updateFilters({ source: v })}
>
  ...
</Select>
```

Update the result count indicator to show `data.count` instead of `filtered.length`.

Update `toggleAll` to toggle all visible rows (`data.data`):

```typescript
const toggleAll = () => {
  const ids = data.data.map((a) => a.id)
  if (selected.size === ids.length && ids.every((id) => selected.has(id))) {
    setSelected(new Set())
  } else {
    setSelected(new Set(ids))
  }
}
```

Update pagination to navigate via URL:

```typescript
const setPage = (p: number) => {
  navigate({
    search: (prev) => ({ ...prev, page: p }),
    replace: true,
  })
}
```

- [ ] **Step 5: Run frontend build checks**

Run from repo root:
```bash
cd frontend && pnpm run build
```
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit frontend changes**

```bash
git add frontend/src/routes/_layout/articles/index.tsx
git commit -m "feat: sync article filters and pagination with URL, use backend search"
```

---

## Self-Review

**Spec coverage:**
- Backend `search` param → Task 1
- Backend test → Task 1
- Regenerate client → Task 2
- URL state sync (`page`, `status`, `source`, `search`) → Task 3
- Frontend uses backend filtering → Task 3

**Placeholder scan:** None. All steps include concrete code and exact commands.

**Type consistency:** `searchSchema` fields match `useSearch` destructuring and `ArticlesService.listArticles` parameter map.

---

## Verification Commands

Backend tests:
```bash
cd backend && MONGODB_URL=mongodb://localhost:27018 MONGODB_DB=test_fastapi_app uv run pytest tests/api/routes/test_articles.py -v
```

Frontend build:
```bash
cd frontend && pnpm run build
```

Linter (optional):
```bash
cd backend && bash scripts/lint.sh
cd frontend && pnpm run lint
```
