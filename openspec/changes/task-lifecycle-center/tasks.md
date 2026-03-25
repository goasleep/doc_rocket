## 1. TaskRun 模型与数据库注册

- [x] 1.1 新建 `backend/app/models/task_run.py`：定义 `TaskRun` Beanie Document，以及 `TaskRunPublic`、`TaskRunsPublic` schemas；所有可选字段有默认值（参见 design.md 决策 1）
- [x] 1.2 在 `backend/app/models/__init__.py` 导出 `TaskRun`、`TaskRunPublic`、`TaskRunsPublic`
- [x] 1.3 在 `backend/app/core/db.py` 的 `init_beanie()` 调用中加入 `TaskRun`

## 2. 分析任务接入 TaskRun

- [x] 2.1 修改 `backend/app/api/routes/analyses.py` 的 `POST /analyses/`：
  - 在现有 `TriggerAnalysisRequest` 中新增 `triggered_by: Literal["manual","agent"] = "manual"` 和 `triggered_by_label: str | None = None`
  - `apply_async()` 调用前先创建并保存 `TaskRun(status="pending", entity_type="article", entity_id=body.article_id, triggered_by=body.triggered_by, triggered_by_label=body.triggered_by_label)`
  - 将 `task_run_id` 作为 `kwargs` 传入 `apply_async()`，拿到返回的 `result` 后回填 `task_run.celery_task_id = result.id` 并保存
- [x] 2.2 修改 `backend/app/tasks/analyze.py` 的 `_analyze_article_async()`：
  - 新增 `task_run_id: str` 参数（所有调用路径都会传入，无需判空）
  - 进入时：将 TaskRun 更新为 `status="running"`, `started_at=now()`
  - 成功时：更新 `status="done"`, `ended_at=now()`
  - 失败时：更新 `status="failed"`, `error_message=str(exc)[:500]`（在现有 article revert 逻辑之后）
- [x] 2.3 `analyze_article_task` Celery task 函数签名同步更新，接收并传递 `task_run_id`

## 3. 抓取任务接入 TaskRun

- [x] 3.1 修改 `backend/app/tasks/fetch.py` 的 `fetch_source_task`：
  - 任务开始时创建 `TaskRun(task_type="fetch", triggered_by="scheduler", entity_type="source", entity_id=source_id, entity_name=source.name)`
  - 成功时更新 `status="done"`；失败时更新 `status="failed"` + `error_message`
  - 为每篇新入库文章 enqueue `analyze_article_task` 之前，先创建 `TaskRun(task_type="analyze", triggered_by="scheduler", entity_type="article", entity_id=article.id, entity_name=article.title)`；拿到 `apply_async()` 返回值后回填 `celery_task_id`；将 `task_run_id` 随 `kwargs` 传入

- [x] 3.2 修改 `backend/app/tasks/fetch.py` 的 `fetch_url_and_analyze_task`：
  - 任务开始时创建 fetch TaskRun：`TaskRun(task_type="fetch", triggered_by="manual")`，此时 `entity_type`/`entity_id` 均为 `None`
  - URL 去重命中（文章已存在）时：回填 `entity_type="article"`, `entity_id=existing_article.id`, `entity_name=existing_article.title`，更新 `status="done"` 后直接返回，不再创建 analyze TaskRun
  - article 新建成功后：回填 fetch TaskRun 的 `entity_type="article"`, `entity_id=article.id`, `entity_name=article.title`
  - 调用 `analyze_article_task.apply_async()` 之前，创建 analyze TaskRun：`TaskRun(task_type="analyze", triggered_by="manual", entity_type="article", entity_id=article.id, entity_name=article.title)`；回填 `celery_task_id`；将 `task_run_id` 随 `kwargs` 传入
  - fetch TaskRun 失败时：更新 `status="failed"` + `error_message`

## 4. 仿写任务接入 TaskRun

- [x] 4.1 修改 `backend/app/api/routes/workflows.py` 的 `POST /workflows/`：WorkflowRun 创建并 `.delay()` 后，立即创建对应 TaskRun：
  - 有关联文章（`body.article_ids` 非空）：先 `await Article.find_one(Article.id == body.article_ids[0])` 取 title，再创建 `TaskRun(task_type="workflow", entity_type="article", entity_id=body.article_ids[0], entity_name=article.title, workflow_run_id=run.id)`
  - topic-only（`body.article_ids=[]`）：`TaskRun(task_type="workflow", entity_type=None, entity_id=None, entity_name=body.topic[:100], workflow_run_id=run.id)`
- [x] 4.2 修改 `backend/app/tasks/workflow.py` 的 `_writing_workflow_async()`：
  - 任务开始时通过 `TaskRun.find_one(TaskRun.workflow_run_id == UUID(workflow_run_id))` 查到对应 TaskRun
  - 更新为 `status="running"`, `started_at=now()`, `celery_task_id=run.celery_task_id`
  - 成功时更新 `status="done"`, `ended_at=now()`
  - 失败时更新 `status="failed"`, `error_message=str(exc)[:500]`

## 5. TaskRun API 路由

- [x] 5.1 新建 `backend/app/api/routes/task_runs.py`：
  - `GET /task-runs`：支持 `task_type`/`status`/`triggered_by`/`entity_id`/`date_from`/`date_to` 筛选，`skip`/`limit` 分页（默认 limit=50），按 `created_at DESC` 排序；返回 `TaskRunsPublic { count, data }`，其中 `count` 为满足筛选条件的总记录数
  - `GET /task-runs/{id}`：返回单条 `TaskRunPublic`，不存在时 404
  - 认证：需要 `CurrentUser`
- [x] 5.2 在 `backend/app/api/main.py` 注册 `/task-runs` 路由

## 6. 重新生成前端客户端 SDK

- [x] 6.1 运行 `bash scripts/generate-client.sh`，确认 `frontend/src/client/` 中出现 `TaskRunPublic`、`TaskRunsPublic` 相关类型和 `TaskRunsService`

## 7. 前端：任务中心页面

- [x] 7.1 新建 `frontend/src/routes/_layout/tasks.tsx`：
  - 顶部 Filter Bar：类型下拉（全部/分析/抓取/仿写）、状态下拉（全部/待处理/运行中/完成/失败）、来源下拉（全部/手动/定时/Agent）
  - 任务表格列：「类型 badge」「关联实体（链接；entity_id 为 None 时展示 entity_name 文字）」「来源 badge」「状态 badge（失败时 tooltip 显示 error_message）」「耗时（started_at/ended_at 均有值时计算，否则显示 —）」「创建时间」
  - 仿写任务行点击 → 跳转 `/workflow?run_id=<workflow_run_id>`
  - TanStack Query 轮询：`refetchInterval: 5000`，当列表中无 `running`/`pending` 任务时停止轮询
- [x] 7.2 `TriggeredByBadge` 组件（可内联或抽取）：
  - `manual` → "手动"（secondary）
  - `scheduler` → "定时"（outline，Clock 图标）
  - `agent` → "Agent · {label}"（blue outline，Bot 图标）

## 8. 前端：侧边栏加入口

- [x] 8.1 修改 `frontend/src/components/Sidebar/AppSidebar.tsx`：在「工作流」附近加「任务中心」导航项（`ListTodo` 图标，路由 `/tasks`）

## 9. 前端：文章详情页「任务历史」Tab

- [x] 9.1 修改 `frontend/src/routes/_layout/articles/$id.tsx`：在现有分析结果展示外层包裹 Tabs，加「分析结果」和「任务历史」两个 Tab
- [x] 9.2 「任务历史」Tab 内容：
  - 第一条节点固定为「入库」（时间 = `article.created_at`，`input_type` 作为说明）
  - 查询 `GET /task-runs?entity_id={article.id}` 并按 `created_at` 升序排列
  - 每条 TaskRun 渲染为时间线节点：类型图标 + 时间 + 来源 badge + 状态（失败时展示 `error_message`）+ 耗时
  - `task_type="workflow"` 的节点附「查看仿写详情 ↗」链接（跳转 `/workflow?run_id=...`）

## 10. 测试

### 后端单元测试

- [x] 10.1 新建 `backend/tests/unit/test_task_run_model.py`：
  - TaskRun 默认值（`status="pending"`, `triggered_by="manual"`, `entity_id=None`, `entity_type=None`）
  - `entity_type`/`entity_id` 可为 None（topic-only 和 fetch_url 创建时的合法状态）
  - `entity_name` 可为 None
  - `error_message` 截断逻辑（超 500 chars 的异常字符串截断至 500）
  - `workflow_run_id` 为 None 时仍可正常保存

### 后端集成测试 — GET /task-runs API

- [x] 10.2 新建 `backend/tests/integration/api/test_task_runs.py`：
  - 未登录访问 `GET /task-runs` → 401
  - 无筛选：按 `created_at DESC` 返回，`count` 反映 DB 中总记录数而非当页数量
  - `task_type=analyze` 筛选：只返回分析任务
  - `task_type=fetch` 筛选：只返回抓取任务
  - `status=failed` 筛选：只返回失败任务
  - `triggered_by=manual` / `triggered_by=scheduler` / `triggered_by=agent` 筛选正确
  - `entity_id=<uuid>` 只返回该文章/来源的任务
  - `date_from` / `date_to` 范围筛选（含边界值）
  - `skip/limit` 分页：第一页与第二页无重叠
  - `GET /task-runs/{id}` 存在 → 200，字段完整
  - `GET /task-runs/{id}` 不存在 → 404

### 后端集成测试 — 分析任务

- [x] 10.3 新建 `backend/tests/integration/api/test_analyses_task_run.py`：
  - `POST /analyses/` 触发后 DB 中存在对应 TaskRun，`status="pending"`，`entity_id` 已设置
  - TaskRun 的 `celery_task_id` 在触发后非空
  - `triggered_by` 传入非法值（如 `"scheduler"`）→ 422
  - `triggered_by="manual"` 默认值正确存储
  - `triggered_by="agent"` + `triggered_by_label` 正确存储
  - 分析开始后 `TaskRun.status="running"`，`started_at` 非空
  - 分析成功后 `TaskRun.status="done"`，`ended_at` 非空
  - 分析失败后 `TaskRun.status="failed"`，`error_message` 非空且长度 ≤ 500

### 后端集成测试 — 抓取任务

- [x] 10.4 新建 `backend/tests/integration/api/test_fetch_task_run.py`：
  - `fetch_source_task` 执行后：
    - 创建 fetch `TaskRun(triggered_by="scheduler", entity_type="source")`，`entity_id` 正确
    - 成功 → fetch TaskRun `status="done"`
    - 失败 → fetch TaskRun `status="failed"` + `error_message`
    - 有新文章时：为每篇文章创建 analyze `TaskRun(triggered_by="scheduler", entity_type="article")`，`celery_task_id` 非空
    - 无新文章时：不创建任何 analyze TaskRun
  - `fetch_url_and_analyze_task` 执行后（URL 为新地址）：
    - 创建 fetch TaskRun，`entity_id` 在 article 创建后回填，`status="done"`
    - 同时创建 analyze TaskRun，`triggered_by="manual"`，`entity_type="article"`，`celery_task_id` 非空
  - `fetch_url_and_analyze_task` 执行后（URL 已存在，去重命中）：
    - 创建 fetch TaskRun，回填已有 article 的 `entity_id`，`status="done"`
    - 不创建 analyze TaskRun

### 后端集成测试 — 仿写任务

- [x] 10.5 新建 `backend/tests/integration/api/test_workflow_task_run.py`：
  - `POST /workflows/`（有文章）后：DB 中存在 `TaskRun(task_type="workflow", entity_type="article", entity_id=article_ids[0])`，`workflow_run_id` 与 WorkflowRun.id 一致
  - `POST /workflows/`（topic-only，`article_ids=[]`）后：TaskRun 的 `entity_type=None`，`entity_id=None`，`entity_name` 包含 topic 文字
  - `writing_workflow_task` 开始执行后：TaskRun `status="running"`，`started_at` 非空，`celery_task_id` 非空
  - 工作流成功完成后：TaskRun `status="done"`，`ended_at` 非空
  - 工作流失败后：TaskRun `status="failed"`，`error_message` 非空且长度 ≤ 500
  - 通过 `GET /task-runs/{id}` 能查到该 TaskRun

### 前端 E2E 测试

- [x] 10.6 新建 `frontend/tests/tasks.spec.ts`：
  - 任务中心页面可访问（`/tasks`），展示任务列表和表头
  - `task_type=analyze` 筛选后只显示分析类型任务
  - `status=failed` 筛选后只显示失败任务
  - `triggered_by=agent` 筛选后显示 Agent badge（含 Bot 图标和 label）
  - `triggered_by=scheduler` 筛选后显示定时 badge（含 Clock 图标）
  - 仿写任务行点击 → 跳转到 `/workflow?run_id=...`
  - 失败任务 hover 显示 `error_message` tooltip
  - topic-only 工作流任务行：关联实体列显示 topic 文字（非空）
  - 有进行中任务时页面持续轮询（数据自动刷新）
  - 无 running/pending 任务时轮询停止（网络请求不再发出）
  - 文章详情页存在「任务历史」Tab
  - 「任务历史」Tab 时间线第一条节点为「入库」，时间与文章创建时间一致
  - 失败的分析任务在时间线中显示 `error_message`
  - `task_type="workflow"` 的时间线节点显示「查看仿写详情 ↗」链接
