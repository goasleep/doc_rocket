## Why

内容创作者和运营团队需要大量高质量的参考素材，但手动收集、分析、仿写爆款内容效率极低，且难以系统化沉淀。本系统通过多Agent流水线将"订阅源抓取 → AI拆解分析 → 素材落库 → 智能仿写"全链路自动化，让内容生产效率大幅提升。

## What Changes

- **新增订阅源管理**：支持 API/RSS 类型订阅源的 CRUD，Celery Beat + celery-redbeat 定时自动抓取，支持动态调度和手动触发
- **新增文章分析管道**：抓取/投稿后自动触发 AI 拆解（hook类型/写作框架/情绪触发/金句/质量评分），全量落库，Celery 异步执行
- **新增多Agent仿写管道**：Writer → Editor → Reviewer 三Agent协作，支持多篇文章作为参考素材，Celery 异步队列执行，SSE 实时推流，最终人工审核
- **新增素材库**：已分析文章作为素材来源，支持质量评分排序筛选，文章列表支持多选触发仿写
- **新增Agent配置中心**：可视化配置每个 Agent 的角色、职责、system_prompt、模型选择（Kimi/Claude/OpenAI），预置默认 Writer/Editor/Reviewer 三个 Agent
- **新增多模型统一接口**：默认 Kimi（moonshot-v1-32k），支持 Claude 和 OpenAI，模型可按 Agent 粒度切换，API Keys 加密存储于 MongoDB
- **新增实时工作流 Chatbot 窗口**：SSE 推流展示每个 Agent 的执行过程，支持轮询降级，含人工审核面板（Reviewer checklist + Editor 3个标题候选）
- **新增仿写稿件编辑器**：Markdown 编辑器 + 去AI味局部重写工具 + 版本历史 + 导出
- **新增手动投稿入口**：独立 /submit 页面，支持粘贴全文或 URL 两种模式，提交后自动触发分析
- **扩展系统设置页面**：API Keys 配置、调度频率、默认模型选择

## Capabilities

### New Capabilities

- `source-management`: 订阅源的 CRUD 管理，支持 API/RSS 类型，含 celery-redbeat 动态调度和手动触发
- `article-ingestion`: 文章抓取与入库，支持自动（来自订阅源）和手动投稿两种方式，入库后自动触发分析
- `article-analysis`: AI 驱动的文章拆解分析，生成结构化素材（hook/框架/情绪/金句/质量评分），Celery 异步执行
- `agent-config`: Agent 角色配置管理（writer/editor/reviewer/custom），含 system_prompt 和模型选择，预置默认三角色
- `writing-workflow`: 多 Agent 协作仿写流水线，支持多篇参考文章，Celery 队列执行，SSE 实时推流，含人工审核和驳回重跑
- `draft-management`: 仿写稿件的存储、Markdown 编辑、版本历史、局部去AI味重写、审批和导出
- `llm-abstraction`: 统一多模型接口层（Kimi/Claude/OpenAI），支持运行时切换
- `system-config`: 系统参数配置（API Keys Fernet加密存储、调度频率、模型默认值）
- `testing-strategy`: 测试体系（LLM mock 策略、Celery 直接测试异步函数、fakeredis、SSE 流测试、respx HTTP mock、fixture 工厂）

### Modified Capabilities

<!-- 无已有 spec 需修改 -->

## Impact

**后端新增文件：**
- `backend/app/api/routes/`: sources, articles, submit, analyses, agents, workflows (SSE), drafts, system_config
- `backend/app/models/`: 独立 models 目录（迁移自 models.py），含 Source, Article, ArticleAnalysis, AgentConfig, WorkflowRun, Draft, SystemConfig
- `backend/app/tasks/`: fetch, analyze, workflow（含 fetch_url_and_analyze），rewrite（Celery 任务，内部用 asyncio.run() 包 Beanie 调用）
- `backend/app/core/llm/`: 多模型统一接口（base, kimi, claude_client, openai_client, factory）
- `backend/app/core/agents/`: 各 Agent 实现（base, fetcher, analyzer, writer, editor, reviewer）
- `backend/app/core/redis_client.py`: Redis 连接（async + sync），pub/sub 辅助函数
- `backend/app/core/encryption.py`: Fernet 加密工具
- `backend/app/celery_app.py`: Celery 应用实例（celery-redbeat 调度器）

**后端修改文件：**
- `backend/app/api/main.py`: 注册新路由
- `backend/app/core/db.py`: 注册新 Beanie 文档模型，播种默认 AgentConfig
- `backend/app/main.py`: lifespan 不再启动 APScheduler（改由独立 celery-beat 进程管理）
- `backend/pyproject.toml`: 新增依赖（openai, anthropic, celery[redis], celery-redbeat, feedparser, httpx, cryptography）

**前端新增文件：**
- `frontend/src/routes/_layout/`: sources, submit, articles/index, articles/$id, agents, workflow, drafts/index, drafts/$id

**前端修改文件：**
- `frontend/src/routes/_layout.tsx`: 扩展侧边栏导航
- `frontend/src/routes/_layout/settings.tsx`: 扩展系统配置
- `frontend/src/hooks/`: useSSE, useWorkflowPolling（新增）

**基础设施：**
- `docker-compose.yml`: 新增 redis, celery-worker, celery-beat, flower(可选) services

**数据库：** 新增 7 个 MongoDB collections（sources, articles, article_analyses, agent_configs, workflow_runs, drafts, system_config）
