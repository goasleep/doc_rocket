## Why

当前每个 agent（WriterAgent、EditorAgent、ReviewerAgent）只执行单次 LLM 调用，无法使用工具、无法加载指令包、无法进行多步推理，本质上是一个"被动文本转换器"而非真正的 agent。随着内容智能需求增长，agent 需要能够自主搜索信息、加载领域知识、在多步推理中完成复杂任务。

## What Changes

- **新增 Skill 系统**：Skill 存入 MongoDB，包含 name、description、body（指令）、可选脚本；支持从社区标准 SKILL.md 格式（agentskills.io）导入
- **新增 Tool 系统**：Tool 元数据存入 MongoDB，幂等种子脚本预填充内置工具（web_search、fetch_url、activate_skill、run_skill_script、query_articles、save_draft）；执行层分 Python 函数（内置）和脚本执行（LocalExecutor，接口预留 DockerExecutor）
- **Agent Loop 改造**：所有 agent 从单次 `llm.chat()` 改为 agentic event loop（推理 → tool_call → 执行 → 观察 → 继续，直到无 tool_call）
- **新增 OrchestratorAgent**：作为 Leader 协调 Writer/Editor/Reviewer 团队，支持非线性路由（Editor 可将工作打回 Writer 重写）
- **LLM 接口升级**：`LLMClient.chat()` 支持 `tools` 参数，返回 `ChatResponse`（文本或 tool_calls 列表）；移除 Claude 相关代码，只保留 OpenAI 格式和 Kimi
- **AgentConfig 扩展**：新增 `skills`、`tools`、`max_iterations` 字段
- **新增 WorkflowRun 模型**：追踪 agentic 执行状态、消息历史、各 sub-agent 执行轨迹

## Capabilities

### New Capabilities

- `skill-management`: Skill 的 CRUD、从 SKILL.md 格式导入转化、skill catalog 注入 agent context
- `tool-management`: Tool 元数据管理、内置工具注册表、LocalExecutor 脚本执行、DockerExecutor 接口预留
- `agentic-loop`: Agent event loop 核心引擎（推理循环、tool dispatch、最大迭代数限制）
- `orchestrator-agent`: OrchestratorAgent Leader 角色、非线性工作流路由、WorkflowRun 状态追踪

### Modified Capabilities

- `llm-abstraction`: `chat()` 方法签名变更（新增 tools 参数，返回类型从 str 改为 ChatResponse）；移除 Claude provider；**BREAKING**
- `agent-config`: 新增 skills、tools、max_iterations 字段
- `writing-workflow`: 工作流执行引擎改为通过 OrchestratorAgent 驱动，替代原有线性 pipeline

## Impact

- **Backend 代码**：`core/llm/`（接口升级、删除 claude_client.py）、`core/agents/`（全部改造）、`models/`（新增 Skill、Tool、WorkflowRun）、`api/routes/`（新增 skills、tools 路由）
- **数据库**：新增 `skills`、`tools`、`workflow_runs` collections；AgentConfig collection 新增字段
- **依赖**：新增 `tavily-python`（web_search）；`httpx`（fetch_url）、`pyyaml`（SKILL.md 解析）已存在或按需确认
- **前端**：需新增 Skill 管理页面和 Tool 管理页面（UI 层变更不在本 change 范围内，仅提供 API）
