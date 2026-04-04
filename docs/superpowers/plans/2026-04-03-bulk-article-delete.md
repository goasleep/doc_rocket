# 批量删除文章 + 前端分页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为文章库增加后端批量删除 API 和前端分页，并支持勾选后批量物理删除文章及其关联分析数据。

**Architecture:** 后端新增 `POST /articles/bulk-delete` 端点，使用 Beanie `delete_many` 先删 `ArticleAnalysis` 再删 `Article`；前端在文章列表引入分页状态，复用现有 `skip`/`limit` API，并在选择工具栏增加"批量删除"按钮。

**Tech Stack:** FastAPI + Beanie + MongoDB / React 19 + TanStack Query + shadcn/ui + 自动生成 client

---

## File Mapping

| File | Responsibility |
|------|----------------|
| `backend/app/api/routes/articles.py` | 新增 `POST /articles/bulk-delete` 端点 |
| `backend/tests/api/routes/test_articles.py` | 新增批量删除 API 测试 |
| `frontend/src/routes/_layout/articles/index.tsx` | 添加分页、批量删除按钮、清空选择逻辑 |
| `frontend/src/client/sdk.gen.ts` | 自动生成，新增 `bulkDeleteArticles` 方法（由 `generate-client.sh` 生成） |

---

### Task 1: 后端批量删除端点

**Files:**
- Modify: `backend/app/api/routes/articles.py`
- Test: `backend/tests/api/routes/test_articles.py`

- [ ] **Step 1: 定义请求模型**

在 `backend/app/api/routes/articles.py` 中，于 `ArticleTitleUpdate` 类下方添加：

```python
class BulkDeleteRequest(BaseModel):
    ids: list[uuid.UUID]
```

- [ ] **Step 2: 实现 `POST /articles/bulk-delete` 端点**

在 `backend/app/api/routes/articles.py` 末尾（`archive_article` 函数之后）添加：

```python
@router.post("/bulk-delete")
async def bulk_delete_articles(current_user: CurrentUser, body: BulkDeleteRequest) -> dict[str, Any]:
    if not body.ids:
        raise HTTPException(status_code=400, detail="ids cannot be empty")
    # Delete associated analyses first
    await ArticleAnalysis.find(ArticleAnalysis.article_id.in_(body.ids)).delete_many()
    # Delete articles
    delete_result = await Article.find(Article.id.in_(body.ids)).delete_many()
    return {"deleted_count": delete_result.deleted_count}
```

确保文件顶部已导入 `ArticleAnalysis`（检查已有 `from app.models import Article, ArticleAnalysis, ...`）。

- [ ] **Step 3: 编写测试**

在 `backend/tests/api/routes/test_articles.py` 中（如不存在则创建），添加测试：

```python
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models import Article, ArticleAnalysis
from app.core.db import init_db


@pytest.fixture(scope="session")
async def db():
    await init_db()
    yield
    await Article.find_all().delete_many()
    await ArticleAnalysis.find_all().delete_many()


@pytest.fixture
async def client(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_bulk_delete_articles(client: AsyncClient):
    # Create test articles and analyses
    article1 = Article(title="A1", content="c1")
    article2 = Article(title="A2", content="c2")
    article3 = Article(title="A3", content="c3")
    await article1.insert()
    await article2.insert()
    await article3.insert()

    analysis1 = ArticleAnalysis(article_id=article1.id, quality_score=50)
    analysis2 = ArticleAnalysis(article_id=article2.id, quality_score=60)
    await analysis1.insert()
    await analysis2.insert()

    response = await client.post("/api/v1/articles/bulk-delete", json={
        "ids": [str(article1.id), str(article2.id)]
    })
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2

    remaining_article = await Article.find_one(Article.id == article3.id)
    assert remaining_article is not None

    deleted_analysis1 = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == article1.id)
    deleted_analysis2 = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == article2.id)
    assert deleted_analysis1 is None
    assert deleted_analysis2 is None
```

**注意：** 由于项目已有测试 fixture，请先查看 `backend/tests/conftest.py` 中是否已有 `client` 和 `db` fixture。如果有，复用它们，不要将 fixture 定义写进测试文件。查看后调整测试代码。

- [ ] **Step 4: 运行测试**

```bash
cd /home/smith/Project/full-stack-fastapi-template/backend
MONGODB_URL=mongodb://localhost:27018 MONGODB_DB=test_fastapi_app uv run pytest tests/api/routes/test_articles.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/articles.py backend/tests/api/routes/test_articles.py
git commit -m "feat: add bulk delete articles endpoint with tests"
```

---

### Task 2: 重新生成前端 API client

**Files:**
- Auto-generate: `frontend/src/client/sdk.gen.ts`

- [ ] **Step 1: 运行生成脚本**

确保后端服务正在运行（以生成 OpenAPI schema），然后执行：

```bash
cd /home/smith/Project/full-stack-fastapi-template
bash scripts/generate-client.sh
```

Expected: `frontend/src/client/sdk.gen.ts` 中出现 `bulkDeleteArticles` 方法。

- [ ] **Step 2: 验证生成结果**

```bash
grep -n "bulkDeleteArticles" frontend/src/client/sdk.gen.ts
```

Expected: 有匹配行。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/client/
git commit -m "chore: regenerate client for bulk delete articles"
```

---

### Task 3: 前端分页 + 批量删除

**Files:**
- Modify: `frontend/src/routes/_layout/articles/index.tsx`

- [ ] **Step 1: 添加分页状态并修改数据获取**

修改 `ArticlesTableContent` 组件：

```tsx
  const [page, setPage] = useState(1)
  const pageSize = 10

  const { data } = useSuspenseQuery({
    queryKey: ["articles", page],
    queryFn: () =>
      ArticlesService.listArticles({
        skip: (page - 1) * pageSize,
        limit: pageSize,
      }),
  })
```

同时在选择`useEffect`或逻辑中，切换 `page` 时清空 `selected`：

```tsx
  // Reset selection when page changes
  useState(() => {
    setSelected(new Set())
  }, [page])
```

**更正：** 使用 `useEffect` 导入：

```tsx
import { Suspense, useEffect, useState } from "react"
```

并在组件内添加：

```tsx
  useEffect(() => {
    setSelected(new Set())
  }, [page])
```

- [ ] **Step 2: 添加批量删除 mutation**

在 `archiveMutation` 下方添加：

```tsx
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      ArticlesService.bulkDeleteArticles({ requestBody: { ids } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] })
      setSelected(new Set())
      showSuccessToast("批量删除成功")
    },
    onError: () => showErrorToast("批量删除失败"),
  })
```

- [ ] **Step 3: 在选择工具栏添加"批量删除"按钮**

在已有的 `selected.size > 0` 工具栏 `div` 中，于"取消选择"按钮之前插入：

```tsx
          <Button
            size="sm"
            variant="destructive"
            onClick={() => {
              if (
                confirm(
                  `确认删除选中的 ${selected.size} 篇文章？此操作不可恢复。`
                )
              ) {
                bulkDeleteMutation.mutate(Array.from(selected))
              }
            }}
            disabled={bulkDeleteMutation.isPending}
          >
            批量删除
          </Button>
```

- [ ] **Step 4: 添加分页组件**

在 `Table` 下方添加分页组件。首先确认项目已有分页组件路径。如果已有 `src/components/ui/pagination.tsx`，则引入使用；如果没有，请先查看 `frontend/src/components/ui/` 目录。

查看后，在 `Table` 闭合标签之后添加分页：

```tsx
      {data.count > pageSize && (
        <div className="flex justify-center pt-4">
          <Pagination
            page={page}
            totalPages={Math.ceil(data.count / pageSize)}
            onPageChange={setPage}
          />
        </div>
      )}
```

**如果项目没有现成 Pagination 组件**，请使用 shadcn/ui 风格手写一个简单分页条（包含上一页/下一页和页码数字）。

- [ ] **Step 5: 调整"全选"逻辑以适配分页**

`toggleAll` 已经只选当前 `filtered`（即当前页），无需改动。但注意 `filtered` 现在只是一页数据，行为正确。

- [ ] **Step 6: 构建并验证前端**

```bash
cd /home/smith/Project/full-stack-fastapi-template/frontend
pnpm run build
```

Expected: 无 TypeScript 错误。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/routes/_layout/articles/index.tsx
git commit -m "feat: add pagination and bulk delete to articles list"
```

---

## Spec Coverage Check

| 需求 | 对应任务 |
|------|----------|
| 后端批量删除 API | Task 1 |
| 物理删除 Article + ArticleAnalysis | Task 1 Step 2、Step 3 测试验证 |
| 前端分页 | Task 3 Step 1、Step 4 |
| 勾选后才能删除 | Task 3 Step 3（按钮在 selected.size > 0 时显示）+ confirm |
| 刷新列表 | Task 3 Step 2 `onSuccess` 中 invalidateQueries |

## Placeholder Scan

无 TBD/TODO。所有步骤包含实际代码和命令。

## Type Consistency

- `ids` 在请求体中为 `list[uuid.UUID]`（后端）/ `string[]`（前端）。
- `ArticlesService.bulkDeleteArticles` 的签名由生成脚本决定，预期接受 `{ requestBody: { ids: string[] } }`。
