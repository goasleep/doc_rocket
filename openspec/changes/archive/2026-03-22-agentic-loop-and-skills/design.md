## Context

当前架构中，每个 agent 是一个简单的 `async def run(input_text) -> str` 方法，内部只做一次 `llm.chat()` 调用。LLM 接口（`LLMClient.chat()`）只返回 `str`，不支持 tool_calls。工作流在 `tasks/workflow.py` 中以硬编码线性顺序执行：Writer → Editor → Reviewer，由 Celery task 驱动。

两个 LLM client（`KimiClient` 和 `OpenAIClient`）都基于 `AsyncOpenAI` SDK，行为几乎完全一致（Kimi 使用自定义 `base_url`），这意味着 function calling 升级只需改一处公共逻辑。`ClaudeClient` 依赖 `anthropic` SDK，与 OpenAI 格式不兼容，可以直接删除。

## Goals / Non-Goals

**Goals:**
- LLM 接口支持 OpenAI function calling 格式，返回结构化 `ChatResponse`
- 所有 agent 具备真正的 event loop（多步推理 + 工具调用）
- Skills 和 Tools 元数据存入 MongoDB，运行时动态加载
- OrchestratorAgent 替代硬编码 pipeline，支持非线性路由（打回重写）
- LocalExecutor 支持在本地执行 Skill 携带的脚本，接口预留 DockerExecutor

**Non-Goals:**
- DockerExecutor 的具体实现（仅设计接口）
- 前端 Skills/Tools 管理 UI（仅提供 API）
- Agent 之间的异步消息传递（Orchestrator 通过直接 Python 调用协调，不引入 mailbox）
- 分布式 multi-process agent team（所有 agent 在同一进程内运行）

## Decisions

### 1. LLM 接口：引入 ChatResponse，删除 Claude

**决策**：`LLMClient.chat()` 返回类型从 `str` 改为 `ChatResponse`，新增 `tools` 参数。删除 `ClaudeClient`。

```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class ChatResponse:
    content: str | None        # 文本回答（无 tool call 时）
    tool_calls: list[ToolCall] # tool call 列表（有时 content 为 None）

class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,   # OpenAI tool schema 格式
        response_format: dict | None = None,
        **kwargs,
    ) -> ChatResponse: ...
```

OpenAI SDK 原生支持此格式。KimiClient 和 OpenAIClient 都基于 `AsyncOpenAI`，升级逻辑完全一致，可提取到公共基类 `OpenAICompatibleClient`。

**替代方案考虑**：保留 `str` 返回，在 agent 层面解析 tool call 标记（ReAct prompt 模式）。放弃原因：不如原生 function calling 可靠，且 Kimi/OpenAI 都已原生支持。

### 2. Tool 执行：静态注册表 + DB 元数据

**决策**：Tool 的 Python 实现以静态注册表（`TOOL_REGISTRY: dict[str, Callable]`）存在于代码中；DB 中的 `Tool` Document 只存元数据（description、parameters_schema、是否启用）。运行时从 DB 拉取 agent 可用的 tools，组装 OpenAI tool schema，注入 LLM 调用。

```
DB: Tool { name, description, parameters_schema, is_active }
Code: TOOL_REGISTRY = { "web_search": web_search_fn, "fetch_url": fetch_url_fn, ... }
运行时：available_tools = [t for t in agent_config.tools if TOOL_REGISTRY.get(t)]
```

**理由**：允许用户通过 UI 启用/禁用工具、修改描述；但工具实现代码仍受版本控制，避免任意代码执行安全风险。

**替代方案考虑**：Tools 存代码到 DB（动态执行）。放弃原因：安全风险高，调试困难。

### 3. Script 执行：ScriptExecutor 抽象 + LocalExecutor

**决策**：引入 `ScriptExecutor` 抽象接口，`LocalExecutor` 作为当前实现，`DockerExecutor` 接口预留。

```python
class ScriptExecutor(ABC):
    @abstractmethod
    async def run(self, command: str, scripts: list[SkillScript],
                  working_dir: str | None = None, timeout: int = 30) -> ExecutionResult: ...

@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int

class LocalExecutor(ScriptExecutor):
    async def run(self, command, scripts, working_dir=None, timeout=30):
        # 1. 写脚本到临时目录
        # 2. subprocess.run(command, cwd=tmpdir, timeout=timeout)
        # 3. 清理临时目录
        # 4. 返回 ExecutionResult
```

`bash` 内置工具调用 `ScriptExecutor.run()`，执行器类型可通过 AgentConfig 或系统配置切换。

### 4. Agent Event Loop

**决策**：`BaseAgent.run()` 改为 agentic loop，直到 LLM 返回纯文本（无 tool_calls）或达到 `max_iterations` 为止。

```
初始化：
  1. 从 DB 加载 agent 的可用 skills（只取 name+description，组装 catalog）
  2. 从 DB 加载 agent 的可用 tools，组装 OpenAI tool schema
  3. 构建初始消息（system prompt + skill catalog + user input）

Loop：
  response = await llm.chat(messages, tools=tools_schema)
  if response.tool_calls:
      for tc in response.tool_calls:
          result = await dispatch_tool(tc.name, tc.arguments)
          messages.append(assistant_msg_with_tool_calls)
          messages.append(tool_result_msg)
      continue
  else:
      return response.content  # done

Skill catalog 注入格式（system prompt 末尾）：
  <available_skills>
    <skill><name>web-research</name><description>...</description></skill>
  </available_skills>
  当任务匹配某 skill 的 description 时，调用 activate_skill(name) 工具加载完整指令。
```

`activate_skill` 是内置工具，从 DB 取出 Skill.body 后以 `<skill_content name="...">...</skill_content>` 格式注入到消息历史。

### 5. OrchestratorAgent：非线性路由

**决策**：新增 `OrchestratorAgent`，其 tools 为 `delegate_to_writer`、`delegate_to_editor`、`delegate_to_reviewer`、`finalize`。Orchestrator 自己也有 event loop，通过 tool call 驱动各 sub-agent 执行，根据返回结果决定路由（可打回）。

```
Orchestrator loop 示例：
  → delegate_to_writer(task, context) → WriterAgent.run() → draft_v1
  → delegate_to_editor(draft_v1) → EditorAgent.run()
      → {approved: false, content: draft_v1, feedback: "结构混乱，需重写导言", title_candidates: [...]}
  → delegate_to_writer(task, context, revision_feedback="结构混乱，需重写导言") → draft_v2
  → delegate_to_editor(draft_v2) → EditorAgent.run()
      → {approved: true, content: draft_v2_revised, feedback: "", title_candidates: [...]}
  → delegate_to_reviewer(draft_v2_revised) → review_result
  → finalize(draft_v2_revised, title_candidates=[...]) → done
```

注：`delegate_to_editor` 始终返回完整的四字段结构 `{approved, content, feedback, title_candidates}`；`approved=false` 时 content 为原稿，`approved=true` 时 content 为编辑修订后的稿件。

Sub-agent（Writer/Editor/Reviewer）各自运行独立的 agentic loop，有自己的 tools 和 skills。Orchestrator 同步等待每个 sub-agent 完成（`await sub_agent.run(...)`），无需消息队列。

**最大迭代数**：Orchestrator 默认 `max_iterations=10`，sub-agents 默认 `max_iterations=5`，可在 AgentConfig 中配置。

### 6. WorkflowRun 模型升级

现有 `WorkflowRun` 模型扩展，新增字段：
- `orchestrator_messages: list[dict]`：Orchestrator 的完整消息历史
- `routing_log: list[RoutingEvent]`：每次路由决策记录（agent、action、reason）
- `iteration_count: int`：Orchestrator 迭代次数

`AgentStep` 扩展：
- `messages: list[dict]`：该 sub-agent 的完整消息历史（包含 tool calls）
- `tools_used: list[str]`：本次执行调用过的工具名（由 AgentRunContext.tools_used set 转换）
- `skills_activated: list[str]`：本次激活过的 skill 名（由 AgentRunContext.skills_activated set 转换）
- `iteration_count: int`：本次执行的 loop 迭代次数（来自 AgentRunContext.iteration_count）

注：AgentRunContext 在 run() 调用期间持有 set 类型；sub-agent 完成后将其转换为 list 写入 AgentStep。

## Risks / Trade-offs

- **loop 无限运行** → AgentConfig.max_iterations 硬上限，超出后强制返回当前最佳输出并标记 `status=interrupted`
- **Tool 执行失败** → tool result 包含错误信息返回给 LLM，agent 自行决定重试或跳过；连续 3 次相同 tool 失败后 loop 终止
- **LLM 不遵从 tool call 格式**（Kimi 偶发） → 回退：检测纯文本中是否有 JSON tool_call 标记，解析失败则当作最终答案
- **LocalExecutor 安全性** → 脚本在服务器进程中执行，有安全风险；通过 timeout（默认 30s）、禁止网络调用的 skill 默认不开网络、后续可换 DockerExecutor 缓解
- **现有 workflow.py 线性逻辑** → 过渡期：新增 `OrchestratorAgent` 路径，保留旧线性路径作为 fallback，由 WorkflowRun.use_orchestrator 字段控制

## Migration Plan

1. 先升级 LLM 接口（ChatResponse），更新所有 agent 的 `.chat()` 调用，保持 loop 为单次（兼容现有行为）
2. 新增 Skill/Tool DB 模型 + 种子脚本；`seed_tools()` 在 `backend/scripts/prestart.sh` 中调用（与 `initial_data.py` 同级），确保容器启动时自动执行
3. 实现 BaseAgent event loop + built-in tool 注册表
4. 实现 OrchestratorAgent，WorkflowRun 新增 `use_orchestrator` flag（默认 False，在 POST /workflows 时根据 SystemConfig.orchestrator.enabled 决定初始值）
5. 充分测试后将 SystemConfig.orchestrator.enabled 默认改为 True，废弃旧线性路径

**回滚**：将 `use_orchestrator` 置为 False 即可回退到旧线性逻辑，不需要数据迁移。

### 7. AnalyzerAgent 特殊处理策略

**决策**：AnalyzerAgent 保留专用 `run() -> dict` 覆写，**不**转换为 tool-calling agentic loop。

AnalyzerAgent 的职责是"给定文章文本，返回结构化分析 dict"，本质上是一次性 JSON 提取任务，不需要多步推理也不需要工具。将其转为 loop 只会增加复杂度而无收益。

实现方式：
```python
class AnalyzerAgent(BaseAgent):
    async def run(self, input_text: str) -> dict[str, Any]:  # 保留 dict 返回
        llm = await self._get_llm()
        response = await llm.chat(
            messages=[...],
            response_format={"type": "json_object"},
            # 不传 tools，走纯 JSON mode 路径
        )
        # ChatResponse.content 包含 JSON 字符串
        raw = response.content or ""
        return json.loads(raw)  # 解析后返回 dict
```

`OpenAICompatibleClient` 在 `response_format=json_object` 且无 tool_calls 时，保证 `ChatResponse.content` 为有效 JSON 字符串。

### 8. web_search 工具后端选型

**决策**：使用 **Tavily Search API**（`tavily-python` SDK）作为 web_search 的后端实现。

**理由**：
- 专为 AI agent 设计，返回结构化结果（title, url, content snippet），无需 HTML 解析
- 有免费 tier（1000 次/月），适合开发阶段
- API 稳定，有官方 Python SDK
- DuckDuckGo 非官方 API 不稳定；Bing/Serper 配置复杂

**配置**：`SystemConfig` 新增 `search.tavily_api_key` 加密字段（与现有 LLM key 管理方式一致）。无 key 时 `web_search` 工具调用返回错误信息，不抛异常。

### 9. SSE 事件扩展（OrchestratorAgent 路径）

OrchestratorAgent 路径新增以下 SSE 事件类型（现有前端事件类型保持不变）：

| 事件类型 | 触发时机 | payload 字段 |
|---|---|---|
| `routing_decision` | Orchestrator 做出路由决策时 | `from_agent`, `to_agent`, `reason` |
| `agent_start` | 已有，sub-agent 开始时复用 | `agent`, `role`, `message` |
| `agent_output` | 已有，sub-agent 完成时复用 | `agent`, `role`, `content`, `title_candidates` |
| `revision_started` | Writer 被打回重写时 | `revision_count`, `feedback_preview` |

前端收到 `routing_decision` 或 `revision_started` 时不需要特殊处理，仅追加到日志显示，保持向后兼容。

## Open Questions

- Kimi moonshot 的 function calling 在非 streaming 模式下行为是否与标准 OpenAI 一致？（需实测验证，parallel_tool_calls 支持情况）
- Skill 脚本的安全策略：LocalExecutor 阶段是否需要限制可导入的模块？
- OrchestratorAgent 是否需要人工审批节点（Editor 打回超过 N 次时暂停等待用户介入）？
- Celery task soft time limit 是否需要根据 max_iterations × 平均 LLM 响应时间动态调整？
