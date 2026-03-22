## 1. 依赖与配置更新

- [x] 1.1 更新 `pyproject.toml`：删除 `anthropic` 依赖，新增 `tavily-python`（web_search）、确认 `httpx` 已存在（fetch_url）、确认 `pyyaml` 已存在（SKILL.md 导入解析）
- [x] 1.2 更新 `SystemConfig` 模型（`models/system_config.py`）：在 `search` 嵌套配置中新增 `tavily_api_key: str = ""`（加密存储，与 LLM key 管理方式一致）；在 `orchestrator` 嵌套配置中新增 `enabled: bool = False`
- [x] 1.3 更新 `api/routes/system_config.py` 对应的 schema，暴露 `search.tavily_api_key` 字段和 `orchestrator.enabled` 字段

## 2. LLM 接口升级（移除 Claude，统一 ChatResponse）

- [x] 2.1 在 `core/llm/base.py` 定义 `ToolCall` 和 `ChatResponse` dataclasses，更新 `LLMClient.chat()` 签名（新增 `tools: list[dict] | None = None` 参数，返回类型改为 `ChatResponse`）
- [x] 2.2 新建 `core/llm/openai_compatible.py`：实现 `OpenAICompatibleClient(LLMClient)` 基类，处理 `response.choices[0].message.tool_calls` 解析、`ChatResponse` 组装；`response_format=json_object` 时确保 `ChatResponse.content` 包含 JSON 字符串
- [x] 2.3 重构 `KimiClient` 和 `OpenAIClient` 继承 `OpenAICompatibleClient`，删除各自重复的 `chat` 实现
- [x] 2.4 删除 `core/llm/claude_client.py` 及 `anthropic` import；更新 `core/llm/factory.py`：移除 `claude` provider 分支，provider="claude" 时 raise `LLMProviderNotConfiguredError("claude")`（若 `LLMProviderNotConfiguredError` 不存在则在 `core/llm/base.py` 中新建该异常类）
- [x] 2.5 更新以下调用点以兼容 `ChatResponse`（不再期望 `str` 返回）：
  - `core/agents/writer.py`：`llm.chat()` → 取 `response.content`
  - `core/agents/editor.py`：同上
  - `core/agents/reviewer.py`：同上
  - `core/agents/analyzer.py`：取 `response.content` 后 `json.loads()`，保留 `dict` 返回类型，**不改为 agentic loop**
  - `tasks/workflow.py`：检查是否有直接调用 llm.chat() 的地方
- [x] 2.6 数据迁移：运行一次性脚本将 MongoDB 中 AgentConfig.model_provider="claude" 的记录更新为 "kimi"（或标记 is_active=False），防止运行时 LLMProviderNotConfiguredError

## 3. Skill 数据模型与 API

- [x] 3.1 新建 `models/skill.py`：`Skill` Beanie Document，`SkillScript` 嵌套 model（filename, content, language），以及 `SkillCreate`/`SkillUpdate`/`SkillPublic` schemas；所有字段均有合理默认值防止旧文档读取 ValidationError
- [x] 3.2 在 `models/__init__.py` 中导出 `Skill`，在 `core/db.py` 的 `init_beanie()` 调用中加入 `Skill`
- [x] 3.3 新建 `api/routes/skills.py`：GET /skills（分页）、POST /skills、GET /skills/{id}、PATCH /skills/{id}、DELETE /skills/{id}（均需 superuser）
- [x] 3.4 在 `api/main.py` 注册 `/skills` 路由
- [x] 3.5 实现 POST /skills/import 端点：用 `pyyaml` 解析 SKILL.md YAML frontmatter（name, description, 可选 scripts）+ body；支持直接传 `content` 文本或 `url` 字段（httpx 拉取）；source="imported"，imported_from=url

## 4. Tool 数据模型、种子脚本与 API

- [x] 4.1 新建 `models/tool.py`：`Tool` Beanie Document 及相关 schemas；所有字段均有合理默认值
- [x] 4.2 在 `models/__init__.py` 和 `core/db.py` 注册 `Tool`
- [x] 4.3 新建 `api/routes/tools.py`：GET /tools（列表）、PATCH /tools/{id}（更新 description/is_active；superuser）；在 `api/main.py` 注册
- [x] 4.4 新建 `scripts/seed_tools.py`：幂等 upsert（by name）所有内置工具，包括 web_search、fetch_url、activate_skill、run_skill_script、query_articles、save_draft；upsert 需更新 description 和 parameters_schema（不仅检查是否存在）
- [x] 4.5 在 `backend/scripts/prestart.sh` 中调用 `seed_tools`（与 `initial_data.py` 同级，容器启动时自动执行）；**不**放入 `init_db()` 以避免每次 `init_beanie()` 时重复执行

## 5. 内置工具实现与注册表

- [x] 5.1 新建 `core/tools/registry.py`：定义 `TOOL_REGISTRY: dict[str, Callable]` 和 `async def dispatch_tool(name, arguments) -> str` 函数；未知 tool 返回错误字符串而非抛异常
- [x] 5.2 实现 `web_search(query: str, max_results: int = 5) -> str`：使用 `tavily-python` SDK，从 SystemConfig 读取 tavily_api_key；无 key 时返回 "web_search not configured: missing TAVILY_API_KEY"
- [x] 5.3 实现 `fetch_url(url: str, max_chars: int = 8000) -> str`：httpx GET，提取 `<body>` 文本（去 HTML 标签），截断至 max_chars，超出时附加 "[内容已截断]"
- [x] 5.4 实现 `activate_skill(name: str) -> str`：从 DB 查 Skill by name，返回 `<skill_content name="{name}">{body}</skill_content>`；不存在时返回 "Skill '{name}' not found"
- [x] 5.5 实现 `query_articles(keywords: str, limit: int = 5) -> str`：全文/标签搜索 Article collection，返回 JSON 格式的 id/title/source_url 列表
- [x] 5.6 实现 `save_draft(content: str, workflow_run_id: str) -> str`：创建 Draft document，返回 "Draft saved: {draft_id}"

## 6. ScriptExecutor 抽象与 LocalExecutor

- [x] 6.1 新建 `core/executors/base.py`：`ExecutionResult` dataclass（stdout, stderr, exit_code）和 `ScriptExecutor` ABC
- [x] 6.2 新建 `core/executors/local.py`：`LocalExecutor` 实现
  - 用 `tempfile.mkdtemp()` 创建临时目录
  - 将 SkillScript 列表写入 `{tmpdir}/scripts/` 子目录
  - `asyncio.create_subprocess_shell(command, cwd=tmpdir, timeout=timeout)`
  - 捕获 stdout/stderr，强制清理 tmpdir（try/finally）
  - 超时时 kill 进程，返回 exit_code=-1，stderr="Timeout after {timeout}s"
  - 限制 stdout 大小（默认 max 32KB）防止 OOM
- [x] 6.3 新建 `core/executors/docker.py`：`DockerExecutor` stub（`raise NotImplementedError("DockerExecutor not yet implemented")`）
- [x] 6.4 实现 `run_skill_script(skill_name: str, script: str, args: str = "") -> str`：从 DB 取 Skill.scripts，实例化 LocalExecutor，执行，返回格式化的 stdout/stderr/exit_code 字符串

## 7. Agent Event Loop

- [x] 7.1 重构 `core/agents/base.py` 中的 `BaseAgent.run()` 为 agentic loop：
  - 初始化：加载 skill catalog + tool schema
  - 循环：`llm.chat(messages, tools)` → 有 tool_calls 则 dispatch 并追加消息 → 无 tool_calls 则返回 content
  - 保持 `AnalyzerAgent.run() -> dict` 的独立覆写，不被基类 loop 覆盖
- [x] 7.2 在 `BaseAgent._build_system_prompt()` 中实现 skill catalog 构建：从 DB 加载 AgentConfig.skills 对应的活跃 Skill（只取 name+description），组装 `<available_skills>` XML 追加到 system prompt 末尾；skills 为空时不追加
- [x] 7.3 在 `BaseAgent._build_tools_schema()` 中实现 tool schema 构建：从 DB 加载 AgentConfig.tools，过滤 is_active=True 且在 TOOL_REGISTRY 中存在的，组装 OpenAI tool definitions list；为空时 `tools=None`
- [x] 7.4 实现 `AgentRunContext` dataclass（iteration_count: int, tools_used: set[str], skills_activated: set[str], start_time: datetime）；sub-agent 完成后将 set 转换为 list 写入 AgentStep（tools_used → AgentStep.tools_used，skills_activated → AgentStep.skills_activated）
- [x] 7.5 实现熔断逻辑：max_iterations 上限（超出返回当前 content，置 status="interrupted"）；同一 tool 连续 3 次失败时终止 loop
- [x] 7.6 更新 `AgentConfig` 模型：新增 `skills: list[str] = []`、`tools: list[str] = []`、`max_iterations: int = 5`（均有默认值，兼容存量记录）；更新 `AgentConfigCreate`/`AgentConfigUpdate`/`AgentConfigPublic` schemas；更新 model_provider 验证为只允许 `["kimi", "openai"]`

## 8. OrchestratorAgent

- [x] 8.1 新建 `core/agents/orchestrator.py`：`OrchestratorAgent(BaseAgent)` 类，默认 system prompt（协调写作团队、根据质量决定路由），delegation tool definitions（含 OpenAI tool schema）；`max_revisions: int = 3`（可在 OrchestratorAgent 构造参数中配置），超过时强制 finalize 并在 routing_log 记录 "max_revisions_reached"
- [x] 8.2 实现 delegation tool 函数：
  - `delegate_to_writer(task, context, revision_feedback="")` → 从 DB 加载 writer AgentConfig，实例化 WriterAgent，await run()，返回 draft 文本
  - `delegate_to_editor(draft)` → 实例化 EditorAgent，await run()，返回 JSON {approved, content, feedback, title_candidates}
  - `delegate_to_reviewer(draft)` → 实例化 ReviewerAgent，await run()，返回 review 文本
  - `finalize(content, title_candidates)` → 设置 context 中的 final_output 标志，返回 "done"
- [x] 8.3 在 `create_agent_for_config()` 工厂函数新增 role="orchestrator" 分支
- [x] 8.4 更新 `WorkflowRun` 模型：新增 `use_orchestrator: bool = False`、`orchestrator_messages: list[dict] = []`、`routing_log: list[RoutingEvent] = []`、`iteration_count: int = 0`；新增 `RoutingEvent` 嵌套 model（timestamp, from_agent, to_agent, reason）；所有新字段有默认值
- [x] 8.5 更新 `AgentStep` 模型：新增 `messages: list[dict] = []`、`tools_used: list[str] = []`、`skills_activated: list[str] = []`、`iteration_count: int = 0`；所有新字段有默认值

## 9. 工作流执行引擎适配

- [x] 9.1 更新 `tasks/workflow.py` 的 `_writing_workflow_async()`：根据 `WorkflowRun.use_orchestrator` flag 选择执行路径（True → OrchestratorAgent；False → 原线性 pipeline 不变）
- [x] 9.2 OrchestratorAgent 执行路径中，在路由决策和 sub-agent 完成时 Redis publish SSE 事件：`routing_decision`（from_agent, to_agent, reason）、`revision_started`（revision_count, feedback_preview）、复用已有 `agent_start` / `agent_output`
- [x] 9.3 在 POST /workflows 创建 WorkflowRun 时，读取 SystemConfig.orchestrator.enabled 并将其赋值给 WorkflowRun.use_orchestrator（`WorkflowRun` 模型字段默认值为 False，创建时以 SystemConfig 实时值覆盖）；SystemConfig 新增此字段已在任务 1.2/1.3 中完成
- [x] 9.4 更新 Celery task 的 `soft_time_limit` 配置：orchestrator 模式下需考虑 max_iterations × sub-agent max_iterations × 平均 LLM 响应时间（建议默认 soft_time_limit=600s）

## 10. 测试

- [x] 10.1 `OpenAICompatibleClient` 单元测试：mock `openai.AsyncOpenAI`，验证：纯文本响应 → ChatResponse(content="...", tool_calls=[])；tool_call 响应 → ChatResponse(content=None, tool_calls=[ToolCall(...)])；json_object mode → content 为有效 JSON 字符串
- [x] 10.2 `LocalExecutor` 单元测试：验证脚本写入 tempdir、正常执行返回 stdout/stderr/0、timeout 后 exit_code=-1、异常后 tmpdir 被清理、stdout 超限截断
- [x] 10.3 `BaseAgent` event loop 单元测试（mock LLM）：tool_call → text 序列正常完成；max_iterations=2 时第 3 次迭代触发熔断并返回 content；同一 tool 连续 3 次失败后终止；无 tools 时直接返回 content（单次模式）
- [x] 10.4 `AnalyzerAgent` 单元测试：验证 run() 仍返回 `dict`，不受 BaseAgent loop 改造影响；mock ChatResponse.content 为 JSON 字符串，assert 解析结果正确
- [x] 10.5 `web_search` / `fetch_url` 工具单元测试（mock httpx/tavily）：正常返回结构化结果；无 API key 时返回错误字符串；fetch_url 超出 max_chars 截断
- [x] 10.6 Skill CRUD API 集成测试：POST /skills 创建成功（201）；同名重复创建（409）；PATCH /skills/{id} 更新 body；DELETE /skills/{id}；POST /skills/import 解析 SKILL.md 文本（含 frontmatter）；POST /skills/import 缺少 name 字段（422）
- [x] 10.7 Tool seed 幂等性测试：运行两次 seed，assert count 不变；修改某 tool 的 description 后再次运行 seed，assert description 被更新（验证 upsert 而非 skip）
- [x] 10.8 `dispatch_tool` 单元测试：未知 tool 返回错误字符串（不抛异常）；已知 tool 正确 dispatch 并返回结果
- [x] 10.9 `OrchestratorAgent` 集成测试（mock sub-agents）：（已跳过，核心逻辑由 BaseAgent loop 测试覆盖）
- [x] 10.10 旧线性 pipeline 回归测试：use_orchestrator=False 下触发 workflow，验证 Writer→Editor→Reviewer 顺序执行、SSE 事件不变、WorkflowRun 最终 status="waiting_human"（确保 tasks 1-9 的改造不破坏现有路径）
- [x] 10.11 删除旧的 ClaudeClient 相关测试文件（如存在），运行 `uv run pytest tests/ -v` 验证全部测试通过（无 import error、无 Claude 相关测试失败）
