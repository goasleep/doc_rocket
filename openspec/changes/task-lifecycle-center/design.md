## Context

`WorkflowRun` 已有完善的状态机（6 种状态、`AgentStep` 子文档、`celery_task_id`），但 `analyze_article_task` 和 `fetch_source_task` 完全没有对等的记录机制。三类任务的错误信息都无处落地。

## Goals / Non-Goals

**Goals:**
- 统一的 `TaskRun` 文档作为所有 Celery 任务的"执行日志"
- 前端任务中心页面：跨类型列表，多维筛选，来源 badge
- 文章详情页时间线：展示该文章所有关联任务的历程

**Non-Goals:**
- SSE 实时推送 TaskRun 状态变化（分析任务通常 < 10s，轮询足够）
- 替换 WorkflowRun 模型（TaskRun 仅作轻量封装，详细步骤仍在 WorkflowRun）
- 任务重试 / 取消功能（TaskRun 仅记录，不控制）

## Decisions

### 1. TaskRun 模型设计

**决策**：新增独立集合 `task_runs`，不复用/扩展 `WorkflowRun`。

理由：WorkflowRun 是重量级模型（嵌套 AgentStep、routing_log 等），分析和抓取任务不需要这些字段。TaskRun 保持轻量，仿写任务通过 `workflow_run_id` FK 引用 WorkflowRun。

```python
class TaskRun(Document):
    class Settings:
        name = "task_runs"
        indexes = [
            IndexModel([("entity_id", 1)]),
            IndexModel([("task_type", 1), ("status", 1)]),
            IndexModel([("created_at", -1)]),
            IndexModel([("workflow_run_id", 1)]),  # 仿写任务通过此字段反查 TaskRun
        ]

    id: UUID = Field(default_factory=uuid4)
    task_type: Literal["analyze", "fetch", "workflow"]
    celery_task_id: str | None = None

    # 触发来源
    triggered_by: Literal["manual", "scheduler", "agent"] = "manual"
    triggered_by_label: str | None = None  # Agent 名称，仅 triggered_by="agent" 时有值

    # 关联实体（文章 or 订阅源）
    # - fetch_url_and_analyze_task：创建时 article 尚不存在，entity_id=None，article 创建后回填
    # - topic-only 工作流：无关联文章，entity_id 永远为 None，不回填
    entity_type: Literal["article", "source"] | None = None
    entity_id: UUID | None = None
    entity_name: str | None = None  # 反范式冗余，避免查询时 JOIN

    # 生命周期
    status: Literal["pending", "running", "done", "failed"] = "pending"
    error_message: str | None = None

    # 仿写专用
    workflow_run_id: UUID | None = None

    # 计时
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    ended_at: datetime | None = None
```

状态流转：
```
pending → running → done
                 ↘ failed  (error_message = str(exc)[:500])
```

### 2. 任务创建时机

每种触发路径的 TaskRun 创建位置如下：

| 触发路径 | TaskRun 创建位置 | triggered_by |
|---|---|---|
| `POST /analyses/`（手动/Agent） | 路由层，enqueue 之前 | `manual` 或 `agent` |
| `fetch_source_task` → 抓取 | Celery 任务体内第一行 | `scheduler` |
| `fetch_source_task` → 为每篇新文章触发分析 | Celery 任务体内，enqueue analyze 之前 | `scheduler` |
| `fetch_url_and_analyze_task` → 抓取 | Celery 任务体内第一行，entity 回填 | `manual` |
| `fetch_url_and_analyze_task` → 触发分析 | Celery 任务体内，enqueue analyze 之前 | `manual` |
| `POST /workflows/` | 路由层，WorkflowRun 创建后 | `manual` |

**原则**：能在路由层创建的（分析手动触发、仿写）就放路由层，确保任务失败时 TaskRun 仍存在；必须在任务体内创建的（fetch 系列）在任务第一行创建。

**仿写 entity 处理**：若 `body.article_ids` 非空，取 `article_ids[0]` 作为 `entity_id`；若为 topic-only（`article_ids=[]`），则 `entity_type=None`、`entity_id=None`，将 `body.topic[:100]` 写入 `entity_name`，前端任务列表直接展示 topic 文字，避免关联实体列为空。TaskRun 通过 `workflow_run_id` 与 WorkflowRun 关联。

### 3. `celery_task_id` 赋值策略

| 任务类型 | 赋值时机 | 方式 |
|---|---|---|
| 分析（手动/Agent） | 路由层 `apply_async()` 之后 | `task_run.celery_task_id = result.id; await task_run.save()` |
| 分析（定时，来自 fetch） | fetch 任务体内，enqueue analyze 之前 | `task_run.celery_task_id = result.id`（result 来自 apply_async 返回值） |
| 仿写 | `_writing_workflow_async` 将 TaskRun 更新为 `running` 时 | 从已有的 `run.celery_task_id` 复制 |
| 抓取（fetch_source / fetch_url） | 不记录，保持 `None` | fetch 任务由调度器管理，无需在 TaskRun 层追踪 |

### 4. 错误信息存储

`error_message = str(exc)[:500]`：取异常的字符串表示，截断到 500 字符，足够用户理解错误原因（如 `"Error code: 401 - {'error': {'message': 'Invalid Authentication'}}"`），不存储完整 traceback（避免敏感信息泄露）。

### 5. API 设计

```
GET /task-runs
  Query params:
    task_type:    "analyze" | "fetch" | "workflow"              (可选)
    status:       "pending" | "running" | "done" | "failed"     (可选)
    triggered_by: "manual" | "scheduler" | "agent"              (可选)
    entity_id:    UUID                                          (可选，按文章/来源过滤)
    date_from:    datetime  (ISO8601)                           (可选)
    date_to:      datetime  (ISO8601)                           (可选)
    skip:         int = 0
    limit:        int = 50

  Response: { count: int, data: TaskRunPublic[] }
  Auth: CurrentUser（需登录；全部用户可见全部任务）

GET /task-runs/{id}
  Response: TaskRunPublic
  404 if not found
```

### 6. 前端来源 Badge

| triggered_by | badge 文字 | 样式 |
|---|---|---|
| `manual` | 手动 | secondary（灰） |
| `scheduler` | 定时 | outline（Clock 图标） |
| `agent` | Agent · {label} | blue outline（Bot 图标） |

### 7. 文章生命周期 Tab

文章详情页数据来源：
1. `GET /task-runs?entity_id={article_id}` — 该文章关联的全部 TaskRun（analyze + workflow）
2. 已有的 `article.analysis` — 分析结果（如已完成）
3. 通过 `TaskRun.workflow_run_id` 拼接跳转链接到工作流详情页

时间线节点类型：
- `created`：文章入库（来自 `article.created_at`，always present）
- `analyze`：每一条 `task_type="analyze"` 的 TaskRun
- `workflow`：每一条 `task_type="workflow"` 的 TaskRun

> **已知限制**：仿写任务关联多篇文章时，TaskRun 仅记录 `article_ids[0]`，其余文章的「任务历史」Tab 不会出现该工作流节点。

### 8. 不修改 WorkflowRun 触发来源

WorkflowRun 目前没有 `triggered_by` 字段，本 change 不添加（避免破坏现有工作流逻辑）。仿写的来源信息通过 TaskRun 的 `triggered_by` 字段承载。
