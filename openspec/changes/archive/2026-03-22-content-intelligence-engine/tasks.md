## 1. 依赖与基础设施配置

- [x] 1.1 在 `backend/pyproject.toml` 中添加依赖：`openai`, `anthropic`, `celery[redis]`, `celery-redbeat`, `feedparser`, `httpx`, `cryptography`
- [x] 1.2 在 `frontend/package.json` 中添加依赖：`@microsoft/fetch-event-source`（SSE 认证支持）、`@uiw/react-md-editor`（Markdown 编辑器）
- [x] 1.3 在 `docker-compose.yml` 中新增 `redis` service（image: redis:7-alpine），并为 `backend` service 添加 Redis 依赖
- [x] 1.4 在 `docker-compose.yml` 中新增 `celery-worker` service（复用 backend 镜像，命令：`celery -A app.celery_app worker --loglevel=info`）和 `celery-beat` service（命令：`celery -A app.celery_app beat --scheduler redbeat.RedBeatScheduler`）
- [x] 1.5 可选：新增 `flower` service（`celery -A app.celery_app flower`，端口 5555）用于任务监控
- [x] 1.6 在 `backend/app/core/config.py` 中添加：`REDIS_URL`（默认 `redis://localhost:6379/0`）、`KIMI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`（可选，用于首次启动导入）

## 2. models.py 迁移 + 新数据模型

- [x] 2.1 创建 `backend/app/models/` 目录和 `__init__.py`；将现有 `models.py` 内容迁移为 `models/user.py` 和 `models/item.py`；`__init__.py` 统一重导出确保 `from app.models import User, Item` 路径不变
- [x] 2.2 删除原 `backend/app/models.py`（迁移并验证无误后）
- [x] 2.3 创建 `backend/app/models/source.py`：Source Document（id/name/type/url/api_key/headers/api_config/fetch_config/is_active/last_fetched_at/created_at）；api_config 含 items_path/title_field/content_field/url_field/author_field/published_at_field（RSS 类型不需要）
- [x] 2.4 创建 `backend/app/models/article.py`：Article Document（id/source_id/title/content/url/author/published_at/status/input_type/created_at）
- [x] 2.5 创建 `backend/app/models/analysis.py`：ArticleAnalysis Document（id/article_id/quality_score/quality_breakdown/hook_type/framework/emotional_triggers/key_phrases/keywords/structure/style/target_audience/created_at）
- [x] 2.6 创建 `backend/app/models/agent_config.py`：AgentConfig Document（id/name/role/responsibilities/system_prompt/model_provider/model_id/workflow_order/is_active/created_at）
- [x] 2.7 创建 `backend/app/models/workflow.py`：WorkflowRun Document（id/type/input/status/steps/parent_run_id/user_feedback/celery_task_id/final_output/created_by/created_at）+ AgentStep 嵌入模型（id/agent_id/agent_name/role/input/output/thinking/title_candidates/status/started_at/ended_at）；**celery_task_id 用于 abort 时调用 `celery_app.control.revoke(task_id, terminate=True)`**
- [x] 2.8 创建 `backend/app/models/draft.py`：Draft Document（id/source_article_ids/workflow_run_id/title/title_candidates/content/status/edit_history/created_at）；注意 source_article_ids 是列表（支持多篇参考文章）
- [x] 2.9 创建 `backend/app/models/system_config.py`：SystemConfig Document（singleton，含 llm_providers/scheduler/analysis/writing/redis 配置）
- [x] 2.10 在 `backend/app/core/db.py` 的 `init_beanie()` 中注册所有新 Document 类
- [x] 2.11 在 `backend/app/core/db.py` 的 `init_db()` 中添加 SystemConfig 初始化逻辑（首次创建默认配置，检测环境变量 API Keys 则加密导入）
- [x] 2.12 在 `backend/app/core/db.py` 的 `init_db()` 中添加默认 AgentConfig 播种逻辑：若 AgentConfig 集合为空则创建 Writer（workflow_order=1）、Editor（workflow_order=2）、Reviewer（workflow_order=3）三个默认 Agent，使用 SystemConfig.writing.default_model_provider/model_id 作为模型配置

## 3. 加密工具

- [x] 3.1 创建 `backend/app/core/encryption.py`：实现 Fernet 密钥从 SECRET_KEY 的安全派生（`base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest())`），以及 `encrypt_value(plaintext: str) -> str` 和 `decrypt_value(ciphertext: str) -> str` 工具函数

## 4. Celery 应用与任务定义

- [x] 4.1 创建 `backend/app/celery_app.py`：Celery 应用实例（broker=REDIS_URL，backend=REDIS_URL，redbeat 调度器配置）
- [x] 4.2 创建 `backend/app/tasks/` 目录和 `__init__.py`
- [x] 4.3 创建 `backend/app/tasks/fetch.py`：
  - `fetch_source_task(source_id)`：调用 FetcherAgent 抓取订阅源，跳过已存在 URL 的文章，对每篇**新**文章调用 `analyze_article_task.delay(article_id, task_id=f"analyze_{article_id}")`；**使用唯一 task_id 防止并发重复入队**（Celery 不会重复调度同一 task_id）；同时用 `redis.set(f"fetch_lock:{source_id}", 1, nx=True, ex=300)` 防止同一 Source 并发重复抓取，若锁已存在则跳过本次执行
  - `fetch_url_and_analyze_task(url, user_id)`：用于手动投稿 URL 模式；调用 FetcherAgent 抓取单个 URL 并提取正文，若该 URL 已存在则直接返回 existing article_id（静默复用，不重复创建），否则创建 Article 后调用 `analyze_article_task.delay(article_id, task_id=f"analyze_{article_id}")`
- [x] 4.4 创建 `backend/app/tasks/analyze.py`：`analyze_article_task(article_id)`；**幂等保护**：任务开始时先读取 Article.status，若已是 `"analyzing"` 或 `"analyzed"` 则立即 return（防止并发重复执行）；确认 status=raw 后立即更新为 `"analyzing"`（原子写，Beanie `find_one_and_update`）；然后调用 AnalyzerAgent，保存 ArticleAnalysis，更新 Article.status=`"analyzed"`；失败时 status 回退为 `"raw"` 并记录错误
- [x] 4.5 创建 `backend/app/tasks/workflow.py`：`writing_workflow_task(workflow_run_id)`；**幂等保护**：任务开始时读取 WorkflowRun.status，若已是 `"running"/"waiting_human"/"done"/"failed"` 则 return；否则将 status 更新为 `"running"` 并记录 `celery_task_id`；按 AgentConfig.workflow_order 顺序执行 Agent；每步完成后 `redis.publish(f"workflow:{run_id}", event_json)`；Reviewer 完成后设 status=waiting_human 并退出
- [x] 4.6 创建 `backend/app/tasks/rewrite.py`：`rewrite_section_task(draft_id, selected_text, context)`（调用 EditorAgent 局部重写，返回 rewritten_text）
- [x] 4.7 在所有 Celery task 中使用 `asyncio.run()` 包装 Beanie/Motor 异步操作；每个 task 文件拆分为 `async def _xxx_async()` 纯逻辑层（可被测试直接调用）+ `@celery_app.task def xxx_task()` 包装层（调用 `asyncio.run(_xxx_async())`）
- [x] 4.8 在 `backend/app/celery_app.py` 中通过 `@worker_init.connect` 信号实现 worker 初始化：调用 `asyncio.run(init_db())` 完成 MongoDB 连接建立 + Beanie 文档模型注册（**必须包含所有新旧 Document 类：User, Item, Source, Article, ArticleAnalysis, AgentConfig, WorkflowRun, Draft, SystemConfig**）

## 5. LLM 统一接口层

- [x] 5.1 创建 `backend/app/core/llm/` 目录和 `__init__.py`
- [x] 5.2 创建 `backend/app/core/llm/base.py`：`LLMClient` 抽象基类（chat 方法签名、统一工具调用数据结构、`LLMProviderNotConfiguredError` 异常）
- [x] 5.3 创建 `backend/app/core/llm/kimi.py`：`KimiClient`（AsyncOpenAI + base_url="https://api.moonshot.cn/v1"，API Key 从 SystemConfig 解密读取）
- [x] 5.4 创建 `backend/app/core/llm/claude_client.py`：`ClaudeClient`（anthropic SDK，tool_use 响应统一化）
- [x] 5.5 创建 `backend/app/core/llm/openai_client.py`：`OpenAIClient`（标准 AsyncOpenAI）
- [x] 5.6 创建 `backend/app/core/llm/factory.py`：`get_llm_client(provider, model_id=None)` 工厂函数（未配置时抛 LLMProviderNotConfiguredError）

## 6. Agent 层

- [x] 6.1 创建 `backend/app/core/agents/` 目录和 `__init__.py`
- [x] 6.2 创建 `backend/app/core/agents/base.py`：`BaseAgent`（接收 AgentConfig，持有 LLMClient，`run(input: str) -> AgentStepResult`，工具注册机制）
- [x] 6.3 创建 `backend/app/core/agents/fetcher.py`：`FetcherAgent`（API 类型：使用 httpx + api_config 字段映射；RSS 类型：使用 feedparser 自动解析；手动 URL 投稿：httpx 抓取 + 正文提取）
- [x] 6.4 创建 `backend/app/core/agents/analyzer.py`：`AnalyzerAgent`（JSON mode 结构化输出，ArticleAnalysis schema，内容截断逻辑）
- [x] 6.5 创建 `backend/app/core/agents/writer.py`：`WriterAgent`（接收多篇 ArticleAnalysis 作为参考上下文；支持 parent_run 的 user_feedback 作为修改指导）
- [x] 6.6 创建 `backend/app/core/agents/editor.py`：`EditorAgent`（去AI味处理；强制输出 3 个标题候选，结构化存于 AgentStep.output.title_candidates）
- [x] 6.7 创建 `backend/app/core/agents/reviewer.py`：`ReviewerAgent`（结构化 JSON 输出：fact_check_flags/legal_notes/format_issues，每条含 severity 和 description）

## 7. Redis 工具层

- [x] 7.1 创建 `backend/app/core/redis_client.py`：Redis 连接实例（`redis.asyncio.from_url(REDIS_URL)`，用于 FastAPI SSE 订阅）和同步实例（`redis.from_url(REDIS_URL)`，用于 Celery worker publish）
- [x] 7.2 封装 `publish_workflow_event(run_id, event_type, data)` 和 `subscribe_workflow_events(run_id)` 辅助函数

## 8. 后端 API 路由

- [x] 8.1 创建 `backend/app/api/routes/sources.py`：CRUD + `POST /{id}/fetch`（`fetch_source_task.delay(source_id)`）；增删改时同步更新 celery-redbeat 调度条目；API 类型强制验证 api_config
- [x] 8.2 创建 `backend/app/api/routes/articles.py`：列表（排除 content）、详情（含 content 和 analysis）、软删除
- [x] 8.3 创建 `backend/app/api/routes/submit.py`：`POST /submit`（text 模式直接创建 Article 并 `analyze_article_task.delay(article_id, task_id=f"analyze_{article_id}")`；url 模式 `fetch_url_and_analyze_task.delay(url, user_id)`；均立即返回 article_id 供前端跳转）
- [x] 8.4 创建 `backend/app/api/routes/analyses.py`：`GET /` 列表（按 quality_score 排序）、`GET /{id}` 详情、`POST /` 手动触发（为已存在文章重新分析）
- [x] 8.5 创建 `backend/app/api/routes/agents.py`：AgentConfig CRUD；删除时检查运行中 workflow（返回 409）；`GET /models` 返回已配置 provider 的 model_id 列表
- [x] 8.6 创建 `backend/app/api/routes/workflows.py`：`POST /`（接收 article_ids 列表 + type，`writing_workflow_task.delay(run_id)`，返回 202 + workflow_run_id）、`GET /{id}/stream`（SSE，订阅 Redis channel，使用 Authorization header 认证）、`POST /{id}/approve`（含选中标题）、`POST /{id}/reject`（含反馈，创建子 WorkflowRun + `writing_workflow_task.delay(child_run_id)`）、`POST /{id}/abort`（revoke Celery task）、`GET /`、`GET /{id}`
- [x] 8.7 创建 `backend/app/api/routes/drafts.py`：CRUD + `POST /{id}/approve` + `GET /{id}/export?format=markdown` + `POST /{id}/rewrite-section`（**直接 `await _rewrite_section_async()`** — 用户等待重写结果是同步阻塞操作，不适合入队；响应后立即返回 rewritten_text，前端展示 diff 供用户接受或取消）
- [x] 8.8 创建 `backend/app/api/routes/system_config.py`：`GET /`（API Key 脱敏）、`PATCH /`（superuser only）
- [x] 8.9 在 `backend/app/api/main.py` 中注册所有新路由；所有新路由均需 `CurrentUser` 依赖，system_config 需 `SuperuserDep`

## 9. 前端 API 客户端重新生成

- [x] 9.1 运行 `bash scripts/generate-client.sh` 重新生成 `frontend/src/client/`；注意 `frontend/src/routeTree.gen.ts` 会在 `bun run dev` 或 `bun run build` 时自动重新生成（TanStack Router 文件路由约定），CI 环境需显式执行 `bun run build` 确保 routeTree 更新

## 10. 前端基础设施

- [x] 10.1 创建 `frontend/src/hooks/useSSE.ts`：封装 `@microsoft/fetch-event-source`，携带 Authorization header，支持事件类型监听、自动重连、cleanup on unmount
- [x] 10.2 创建 `frontend/src/hooks/useWorkflowPolling.ts`：每 3s 轮询 `GET /workflows/{id}`，返回与 useSSE 相同的状态接口，作为 SSE 失败的降级方案
- [x] 10.3 在 `frontend/src/components/ui/` 创建 `StatusBadge.tsx`（workflow/article/draft 状态标签）
- [x] 10.4 扩展 `frontend/src/routes/_layout.tsx` 侧边栏导航：订阅源、文章库、手动投稿、Agent配置、工作流、仿写稿件、系统设置

## 11. 前端页面 — 订阅源管理

- [x] 11.1 创建 `frontend/src/routes/_layout/sources.tsx`：订阅源列表（last_fetched_at、is_active 开关、"立即抓取"按钮）
- [x] 11.2 实现订阅源新建/编辑表单（Drawer）：type 选择（API/RSS）；API 类型额外展示 api_config 字段映射表单（items_path/title_field/content_field/url_field）；RSS 类型隐藏 api_config
- [x] 11.3 实现订阅源删除确认弹窗

## 12. 前端页面 — 手动投稿

- [x] 12.1 创建 `frontend/src/routes/_layout/submit.tsx`：独立投稿页，Text 模式（标题+正文）和 URL 模式两个 tab；提交后跳转 `/articles/{id}`（文章创建后立即跳转，页面展示"分析中..."状态）

## 13. 前端页面 — 文章库

- [x] 13.1 创建 `frontend/src/routes/_layout/articles/index.tsx`：文章列表，质量评分排序、状态筛选、来源筛选；支持**多选 checkbox**；选中多篇后底部出现"触发仿写"操作栏
- [x] 13.2 创建 `frontend/src/routes/_layout/articles/$id.tsx`：文章详情，展示原文 + 拆解结果（hook/框架/情绪/金句/结构/风格卡片），含分析进度指示器；在 status=analyzed 时顶部工具栏显示**"重新分析"按钮**（调 `POST /analyses/` 创建新分析任务，完成后刷新页面）
- [x] 13.3 在文章详情页底部添加"触发仿写"按钮（status=analyzed 时启用），点击调 POST /workflows（单篇），获得 run_id 后自动跳转 /workflow?run_id={id}
- [x] 13.4 在文章列表页实现多选触发仿写：选中多篇 → 点"触发仿写" → 调 POST /workflows（article_ids 为选中列表）→ 跳转 /workflow?run_id={id}

## 14. 前端页面 — Agent 配置

- [x] 14.1 创建 `frontend/src/routes/_layout/agents.tsx`：Agent 列表（按 workflow_order 排序）
- [x] 14.2 实现 Agent 新建/编辑表单：角色选择、system_prompt 多行文本框、model_provider/model_id 级联选择
- [x] 14.3 实现 Agent 删除（运行中冲突提示）

## 15. 前端页面 — 工作流 Chatbot

- [x] 15.1 创建 `frontend/src/routes/_layout/workflow.tsx`：从 URL query 参数 `?run_id=xxx` 读取 run_id；提供新建工作流触发面板（选择模式，支持选择多篇文章或输入主题）
- [x] 15.2 实现双模式渲染：status=pending/running 时优先 SSE（useSSE），失败自动降级为轮询（useWorkflowPolling）
- [x] 15.3 实现 Chatbot 模式：每个 AgentStep 展示为对话气泡（含角色图标、展开/折叠输出）；pending 状态显示"排队中..."
- [x] 15.4 实现 Status 模式：step-by-step 进度列表，当前步骤 spinner，已完成步骤可展开 output
- [x] 15.5 实现人工审核面板（workflow_paused 触发）：
   - 最终草稿预览
   - Editor 3 个标题候选（可点选 + 自定义输入）
   - Reviewer 结构化 checklist（fact_check/legal/format，每条可手动勾选核对）
   - 操作按钮：[✅ 批准（含选中标题）] [✏️ 驳回 + 反馈文字] [🚫 终止]
- [x] 15.6 批准：调 POST /workflows/{id}/approve，获得 draft_id 后跳转 /drafts/{id}
- [x] 15.7 驳回：调 POST /workflows/{id}/reject，获得 child_run_id 后跳转 /workflow?run_id={child_run_id}
- [x] 15.8 历史工作流侧边栏：列出所有 WorkflowRun，驳回产生的子 Run 缩进展示

## 16. 前端页面 — 仿写编辑器

- [x] 16.1 创建 `frontend/src/routes/_layout/drafts/index.tsx`：稿件列表，状态筛选
- [x] 16.2 创建 `frontend/src/routes/_layout/drafts/$id.tsx`：左右双栏 Markdown 编辑器（@uiw/react-md-editor），debounce 1s 自动保存
- [x] 16.3 在编辑器顶部实现标题候选区域：展示 Draft.title_candidates 3 个选项，点击替换当前标题
- [x] 16.4 实现"去AI味"工具：用户选中文字后工具栏按钮激活 → 调 POST /drafts/{id}/rewrite-section → diff 弹窗展示（原文 vs 重写）→ 用户接受或取消
- [x] 16.5 实现版本历史侧边栏：edit_history 时间线，点击预览，点"恢复"替换当前内容
- [x] 16.6 底部操作栏：[导出 .md] [标记为已发布]

## 17. 前端页面 — 系统设置

- [x] 17.1 扩展 `frontend/src/routes/_layout/settings.tsx`：API Keys 配置区（Kimi/Claude/OpenAI，显示脱敏值，修改调 PATCH /system-config）
- [x] 17.2 调度器配置区（默认抓取间隔、最大并发数）
- [x] 17.3 默认模型配置区（分析模型、仿写模型的 provider/model_id 级联选择）

## 18. 测试基础设施搭建

- [x] 18.1 在 `backend/pyproject.toml` dev 依赖组中添加：`fakeredis`, `pytest-mock`, `respx`
- [x] 18.2 创建 `backend/tests/fixtures/` 目录和 `__init__.py`
- [x] 18.3 创建 `backend/tests/fixtures/llm.py`：`mock_llm_chat` fixture（patch `get_llm_client`，返回 AsyncMock，预置 MOCK_ANALYSIS_RESPONSE / MOCK_EDITOR_RESPONSE / MOCK_REVIEWER_RESPONSE 常量）
- [x] 18.4 创建 `backend/tests/fixtures/content.py`：`sample_source`（API类型）、`sample_rss_source`、`sample_article`（status=raw）、`analyzed_article`（含 ArticleAnalysis）、`sample_agent_configs`（writer+editor+reviewer 三个）、`sample_workflow_run`、`sample_draft` 异步 fixture 工厂
- [x] 18.5 创建 `backend/tests/fixtures/content.py` 中的 `fake_redis_sync` 和 `fake_redis_async` fixture（fakeredis.FakeServer 共享，分别 patch sync_redis 和 async_redis）
- [x] 18.6 创建 `backend/tests/tasks/conftest.py`：`celery_config` fixture（task_always_eager=True, task_eager_propagates=True）
- [x] 18.7 在 `backend/tests/conftest.py` 中扩展 `db` fixture 的 cleanup，新增对所有新 Document 类的 `delete_all()`

## 19. 单元测试

- [x] 19.1 创建 `backend/tests/unit/test_encryption.py`：验证 Fernet 密钥派生正确（长度=44字节 base64）、encrypt/decrypt 往返一致、不同 SECRET_KEY 产生不同密钥
- [x] 19.2 创建 `backend/tests/unit/test_llm_factory.py`：验证 get_llm_client("kimi") 返回 KimiClient、"claude" 返回 ClaudeClient、未配置 provider 抛出 LLMProviderNotConfiguredError、默认 model_id 从 SystemConfig 读取
- [x] 19.3 创建 `backend/tests/unit/agents/test_analyzer_agent.py`：验证 AnalyzerAgent 正确解析 MOCK_ANALYSIS_RESPONSE 为 ArticleAnalysis 对象、质量评分范围 0-100、内容截断逻辑（超长文章被截断后仍输出有效分析）
- [x] 19.4 创建 `backend/tests/unit/agents/test_editor_agent.py`：验证 EditorAgent 输出 title_candidates 数组长度恰好为 3、changed_sections 字段存在
- [x] 19.5 创建 `backend/tests/unit/agents/test_reviewer_agent.py`：验证 ReviewerAgent 输出含 fact_check_flags/legal_notes/format_issues，每条含 severity（info/warning/error）和 description
- [x] 19.6 创建 `backend/tests/unit/agents/test_fetcher_agent.py`：使用 respx mock HTTP，验证 API source（api_config 字段映射正确提取 title/content/url）、RSS source（feedparser 自动映射）、手动 URL（正文提取）

## 20. Celery 任务测试

- [x] 20.1 创建 `backend/tests/tasks/test_analyze_task.py`：直接调用 `_analyze_article_async(article_id)`（绕过 Celery 包装），验证：Article.status 变为 analyzed、ArticleAnalysis 被创建入库、quality_score 与 mock 返回一致
- [x] 20.2 创建 `backend/tests/tasks/test_fetch_task.py`：直接调用 `_fetch_source_async(source_id)`，使用 respx mock HTTP 返回 2 条文章，验证：2 个 Article 文档被创建、重复 URL 不创建第二次、Article.status=raw（分析任务入队验证：通过 mock analyze_article_task.delay 确认被调用 2 次）
- [x] 20.3 创建 `backend/tests/tasks/test_workflow_task.py`：直接调用 `_writing_workflow_async(run_id)`，使用 mock_llm_chat 和 fake_redis_sync，验证：Redis channel 收到 agent_start(×3) + agent_output(×3) + workflow_paused(×1) 事件、WorkflowRun.status 变为 waiting_human、AgentStep.title_candidates 含 3 个标题
- [x] 20.4 创建 `backend/tests/tasks/test_rewrite_task.py`：直接调用 `_rewrite_section_async(draft_id, selected_text, context)`，验证返回 rewritten_text 非空且与 mock 返回一致

## 21. API 路由集成测试

- [x] 21.1 创建 `backend/tests/integration/api/test_sources.py`
- [x] 21.2 创建 `backend/tests/integration/api/test_articles.py`
- [x] 21.3 创建 `backend/tests/integration/api/test_submit.py`
- [x] 21.4 创建 `backend/tests/integration/api/test_analyses.py`
- [x] 21.5 创建 `backend/tests/integration/api/test_agents_config.py`
- [x] 21.6 创建 `backend/tests/integration/api/test_workflows.py`
- [x] 21.7 创建 `backend/tests/integration/api/test_drafts.py`
- [x] 21.8 创建 `backend/tests/integration/api/test_system_config.py`

## 22. SSE 流集成测试

- [x] 22.1 创建 `backend/tests/integration/test_sse.py`：
   - test_sse_requires_auth（无 token 返回 401）
   - test_sse_delivers_published_events（用 fake_redis_async 发布 2 条事件，验证 SSE 流按序收到）
   - test_sse_sends_keepalive（mock time.sleep，触发 keepalive 发送，验证 ": keepalive" 行出现在流中）
   - test_sse_closes_on_workflow_done（workflow_done 事件发送后 SSE 连接关闭）
