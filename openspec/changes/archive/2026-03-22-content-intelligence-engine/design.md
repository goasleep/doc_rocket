## Context

现有代码库是一个 FastAPI + Beanie ODM + MongoDB + React 19 全栈模板，已有用户认证（fastapi-users v15）、基础 CRUD（Item）和前端路由（TanStack Router）。

本次在此基础上叠加一个多 Agent 内容智能引擎，新增 7 个 MongoDB 集合、9 组后端路由、多个前端页面，以及完整的 LLM 多模型适配层、Agent 编排引擎和 Celery 异步任务系统。

约束：
- 不破坏现有 User/Item/Auth 体系
- 后端保持 `uv` + `anyio` 异步风格，所有新代码 `async def`
- 前端保持 TanStack Router 文件路由约定，API 客户端通过 `bun run generate-client` 重新生成

## Goals / Non-Goals

**Goals:**
- 订阅源管理（API + RSS）+ Celery Beat 定时抓取，支持动态调度
- AI 文章拆解管道（结构化 JSON 输出 → ArticleAnalysis 入库），**抓取/投稿后自动触发**
- 多 Agent 仿写流水线（Writer → Editor → Reviewer），**支持多篇文章作为参考素材**，Celery 异步执行，SSE 实时推流
- 统一 LLM 接口层，默认 Kimi，支持 Claude / OpenAI，Agent 粒度可配
- API Keys 加密存储于 MongoDB SystemConfig（无需重启切换）
- 前端 Chatbot 工作流窗口（SSE 消费）+ Markdown 仿写编辑器
- 最终人工审核节点
- **全流程闭环不依赖 Chatbot**：通过页面轮询也可完成完整操作流程

**Non-Goals:**
- 一期不含 AI 配图接入
- 一期不含文章溯源功能
- 不做多租户隔离

## Decisions

### D1: LLM 统一接口 — 使用 openai SDK 兼容 Kimi

**决策**：用 `openai` Python SDK 统一驱动 Kimi 和 OpenAI（两者 API 格式相同），Claude 用 `anthropic` SDK 单独适配，由 `LLMClientFactory` 按 `model_provider` 字段路由。

**理由**：Kimi（moonshot）的 API 完全兼容 OpenAI 格式，只需替换 `base_url`。Claude API 格式有差异（tool_use 格式），单独适配更清晰。

**替代方案**：LiteLLM 统一代理 → 调试复杂度高，不选。

---

### D2: SSE 认证 — fetch-event-source + Authorization Header

**决策**：前端使用 `@microsoft/fetch-event-source` 库替代原生 `EventSource`，支持在请求头中携带 `Authorization: Bearer {token}`。

**理由**：原生 `EventSource` 不支持自定义 headers，无法携带 JWT。`fetch-event-source` 用 fetch() 底层模拟 SSE，完整支持自定义 headers 和断线自动重连。

**SSE 跨进程问题**：SSE 事件源改用 Redis pub/sub（见 D3），所有 worker 进程均可订阅同一 channel，多进程部署不再有限制。

---

### D3: 统一任务系统 — Celery + Redis + celery-redbeat

**决策**：引入 Celery 作为统一异步任务和定时任务系统，完全取代 APScheduler，同时 Redis 作为 Celery broker、result backend，以及 SSE 事件广播的 pub/sub 总线。

**定时任务（替代 APScheduler）**：使用 `celery-redbeat` 作为 Celery Beat 调度器，将调度表存储在 Redis 中，支持运行时动态增删改调度任务（每个 Source 有独立调度 entry）。

**异步任务类型**：
```
fetch_source_task(source_id)           ← 定时 + 手动触发
analyze_article_task(article_id)       ← 抓取/投稿后自动触发
writing_workflow_task(workflow_run_id) ← 用户触发仿写
rewrite_section_task(draft_id, ...)    ← 编辑器局部重写
```

**任务自动链**：
- `fetch_source_task` 完成后对每篇新文章自动 `.delay()` `analyze_article_task`
- 手动投稿（/submit）提交后自动 `.delay()` `analyze_article_task`

**SSE 事件流**：Celery worker 执行 `writing_workflow_task` 时，每个 Agent 步骤完成后调用 `redis_client.publish(f"workflow:{run_id}", event_json)`；FastAPI SSE 端点订阅该 channel，用 `fetch-event-source` 推送给前端。

**celery-redbeat 动态调度 API**（Source CRUD 时调用）：
```python
from redbeat import RedBeatSchedulerEntry
from celery.schedules import crontab

# 创建/更新调度（新建或修改 Source 时）
entry = RedBeatSchedulerEntry(
    name=f"fetch_source_{source_id}",
    task="app.tasks.fetch.fetch_source_task",
    schedule=crontab(minute=f"*/{interval_minutes}"),
    args=[str(source_id)],
    app=celery_app
)
entry.save()

# 删除调度（Source 被删除或停用时）
key = RedBeatSchedulerEntry.create_key(f"fetch_source_{source_id}", celery_app)
entry = RedBeatSchedulerEntry.from_key(key, app=celery_app)
entry.delete()
```

**理由**：
- 统一管理所有异步任务和定时任务，无需维护 APScheduler 和 asyncio.Queue 两套机制
- 任务队列解耦：API 请求立即返回，重任务（LLM 调用）在 worker 中排队执行，不阻塞 API
- 解决多进程 SSE 问题：Redis pub/sub 跨进程广播，不再受单 worker 约束
- 内置重试、优先级、Flower 监控
- `celery-redbeat` 支持动态调度，运行时增删 Source 立即生效

**替代方案（已否决）**：
- 保留 APScheduler + asyncio.Queue → 单进程约束无法解决，任务队列功能弱
- Celery + RabbitMQ → RabbitMQ 运维复杂度更高，Redis 既能做 broker 又能做 pub/sub，更合适

**新增基础设施**：`Redis`（作为 broker、result backend、pub/sub）

---

### D4: API Keys 加密存储 — Fernet + SECRET_KEY 派生

**决策**：LLM Provider API Keys 使用 `cryptography.fernet` 加密存储在 MongoDB SystemConfig。

**Fernet 密钥派生方式**（必须显式派生，不能直接使用 SECRET_KEY 字符串）：
```python
import base64, hashlib
from cryptography.fernet import Fernet

# SECRET_KEY 是任意字符串；Fernet 要求 32字节 URL-safe base64 编码密钥
fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
)
fernet = Fernet(fernet_key)

def encrypt_value(plaintext: str) -> str:
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_value(ciphertext: str) -> str:
    return fernet.decrypt(ciphertext.encode()).decode()
```

**说明**：SHA256 将任意长度的 SECRET_KEY 映射为固定 32 字节，base64 编码满足 Fernet 格式要求。SECRET_KEY 已存在于 `.env`，无需新增密钥管理基础设施。

**适用范围**：SystemConfig 中的 LLM API Keys（kimi/claude/openai）。Source.api_key 一期明文存储（后续可按需加密）。

---

### D5: Agent 编排 — Celery Task + 顺序管道 + 人工暂停节点

**决策**：`writing_workflow_task` 是一个 Celery task，在 worker 中顺序执行各 Agent。每步完成后 `redis.publish(f"workflow:{run_id}", event_json)` 广播事件。工作流在 Reviewer Agent 完成后进入 `waiting_human` 状态，通过 MongoDB 轮询等待用户操作（approve/reject/abort）。

**多文章参考**：仿写工作流支持传入 `article_ids: list[UUID]`（多篇），Writer Agent 将所有文章的 ArticleAnalysis 作为参考上下文，生成融合多篇风格的新稿。

**驳回重跑**：用户驳回时，创建新的子 WorkflowRun（`parent_run_id` 指向原 Run，`user_feedback` 存用户修改意见），调 `writing_workflow_task.delay(child_run_id)` 重新排队执行。

**等待人工审核的实现**：`writing_workflow_task` 完成后将 WorkflowRun.status 改为 `waiting_human` 并退出；approve/reject 操作通过 REST 端点触发，驳回时创建子任务并重新入队。

---

### D6: 文章分析结构化输出

**决策**：Analyzer Agent 使用 JSON mode（`response_format={"type": "json_object"}`）直接输出 ArticleAnalysis schema 格式的 JSON，后端 Pydantic 验证后入库。Claude 用 `tool_use` 模拟结构化输出。

---

### D7: models.py → models/ 目录迁移

**决策**：将现有 `backend/app/models.py` 迁移为 `backend/app/models/` 目录；通过 `models/__init__.py` 统一重新导出，保持所有现有 `from app.models import User, Item` 路径不变。

---

### D8: RSS 支持（一期）

**决策**：一期同时支持 API 和 RSS 两种订阅源类型。RSS 使用 `feedparser` 库解析，Atom/RSS 标准字段自动映射（无需 api_config 字段映射配置）；API 类型仍需提供 api_config。

---

### D9: 前端文件路由与全流程闭环

**决策**：新增路由遵循 TanStack Router 文件路由约定。新增 `/submit` 独立手动投稿页。Workflow 页面支持 SSE 模式和轮询降级模式，确保无 Chatbot 也能完成全流程。

**完整页面操作闭环（无 Chatbot 版）**：
```
/sources 配置订阅源 → 开启自动抓取 → 文章自动入库并自动开始分析
/submit  手动投稿（URL 或粘贴全文）→ 提交即自动开始分析
/articles 查看文章列表和分析状态
/articles/{id} 查看拆解结果 → 勾选多篇文章 → 点击"触发仿写"
    ↓ 自动跳转（携带 run_id）
/workflow?run_id=xxx 查看任务进度（SSE 或轮询）
    → Agents 完成后显示审核面板（Reviewer checklist + 3个标题候选）
    → 批准 → 跳转 /drafts/{id}
/drafts/{id} Markdown 编辑 → 去AI味 → 选标题 → 导出/发布
```

## Risks / Trade-offs

**[R1] 引入 Redis 增加基础设施复杂度**
→ 缓解：Redis 单实例即可满足 MVP 需求，Docker Compose 新增 redis service，配置简单。长期收益（任务队列 + SSE pub/sub + 缓存）远大于成本。

**[R2] Celery worker 与 FastAPI 的 Beanie 初始化**
→ 缓解：Celery worker 需独立初始化 MongoDB 连接和 Beanie 文档模型（不能复用 FastAPI lifespan）；在 Celery `worker_init` 信号中调用 `asyncio.run(init_db())` 完成初始化，或使用同步 PyMongo 在 worker 中操作 MongoDB。

**[R3] celery-redbeat 动态调度的操作接口**
→ 缓解：Source CRUD 时同步调用 `redbeat.RedBeatSchedulerEntry` API 增删改调度条目；启动时全量同步 Source 列表与 redbeat entries。

**[R4] 大文章内容超出模型 context window**
→ 缓解：抓取时对超长文章做分段截断（默认 8000 tokens），SystemConfig 可配置最大 token 数。

**[R5] 多篇参考文章导致 context 过大**
→ 缓解：Writer Agent 仅使用每篇文章的 ArticleAnalysis（结构化摘要），而非原文全文，大幅降低 token 占用。

## Migration Plan

1. 新增 Redis service 至 `docker-compose.yml`
2. 迁移 `backend/app/models.py` → `backend/app/models/` 目录
3. `core/db.py` 的 `init_beanie()` 追加新 Document 类
4. 新路由在 `backend/app/api/main.py` 中逐步注册
5. 前端新增页面通过文件路由自动注册
6. 运行 `bash scripts/generate-client.sh` 更新前端 API 客户端

**回滚**：Celery worker 和 FastAPI 独立运行，移除路由注册和 Beanie 模型注册即可还原核心功能。

## Resolved Questions

- Q1 ✅ Celery worker 使用 `asyncio.run()` 包装 Beanie/Motor 调用，在 `@worker_init.connect` 信号中调用 `asyncio.run(init_db())` 完成初始化，保持一套 Beanie 模型（见任务 4.8）
- Q2 ✅ 文章列表页多选 checkbox + 底部"触发仿写"操作栏（见任务 13.1/13.4）；文章详情页单篇触发（见任务 13.3）
- Q3 ✅ Flower 加入 Docker Compose，可选 service（见任务 1.5）
