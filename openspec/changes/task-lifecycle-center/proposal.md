## Why

当前所有 Celery 任务（分析、抓取、仿写）执行后没有应用层持久记录。分析任务失败时，仅将 `Article.status` 从 `analyzing` 静默回滚到 `raw`，错误原因完全丢失，用户只能翻日志排查。抓取任务（`fetch_source_task`）除更新 `Source.last_fetched_at` 外没有任何执行痕迹。这三类任务的状态信息分散在不同集合，无法统一查询。

## What Changes

- **新增 `TaskRun` 集合**：统一记录所有 Celery 任务（分析/抓取/仿写）的执行状态、错误原因、触发来源、耗时；仿写任务通过 `workflow_run_id` 链接到已有 `WorkflowRun`，不重复存储详细步骤
- **`triggered_by` 来源标识**：区分 `manual`（用户手动触发）、`scheduler`（定时任务）、`agent`（由 Chat/Agent 触发，附带 `triggered_by_label` 显示 Agent 名称）
- **任务中心页面**：列表展示全部任务，来源标识 badge，支持按类型/状态/来源/日期筛选，仿写任务行可跳转到工作流详情
- **文章生命周期 Tab**：文章详情页新增「任务历史」Tab，时间线展示从入库到分析到仿写的完整历程，失败任务显示错误原因

## Capabilities

### New Capabilities

- `task-lifecycle`: TaskRun 模型、`GET /task-runs` API（多维筛选+分页）、任务中心前端页面
- `article-lifecycle-view`: 文章详情页任务历史 Tab（时间线，含 TaskRun + 关联 WorkflowRun 链接）

### Modified Capabilities

- `article-analysis`: `POST /analyses/` 增加 `triggered_by` / `triggered_by_label` 参数；任务执行前创建 TaskRun，完成/失败时更新
- `source-management`: `fetch_source_task` 和 `fetch_url_and_analyze_task` 接入 TaskRun 记录（含各自触发的 analyze TaskRun）
- `writing-workflow`: `POST /workflows/` 路由层创建 TaskRun（链接到 WorkflowRun）；`writing_workflow_task` 开始时更新为 running，完成/失败时同步状态

## Impact

- **Backend**：新增 `models/task_run.py`、`api/routes/task_runs.py`；修改 `tasks/analyze.py`、`tasks/fetch.py`、`tasks/workflow.py`、`api/routes/analyses.py`、`api/main.py`、`models/__init__.py`、`core/db.py`
- **数据库**：新增 `task_runs` collection，含 `entity_id` / `task_type+status` / `created_at` / `workflow_run_id` 四个索引
- **前端**：新增任务中心页面 `tasks.tsx`、更新侧边栏、更新文章详情页；重新生成 API 客户端
- **测试**：新增后端集成测试 4 个文件 + 单元测试 1 个文件；新增前端 E2E 测试 1 个文件
