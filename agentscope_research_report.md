# AgentScope 框架调研报告

## 调研日期：2026-04-01

---

## 一、框架概述

### 1.1 什么是 AgentScope

**AgentScope** 是由阿里巴巴通义实验室开源的**企业级多智能体开发框架**，专注于构建基于大型语言模型（LLM）的多智能体应用。它是阿里云百炼 Agent 平台的技术基础，旨在解决多智能体应用开发中的协作协调和 LLM 性能不稳定等挑战。

### 1.2 核心定位

| 维度 | 说明 |
|------|------|
| **目标用户** | 企业级开发者、生产环境部署者 |
| **设计理念** | "企业级智能体操作系统" / "智能体的 Kubernetes" |
| **核心目标** | 高可靠性、可监控性、可扩展性的多智能体系统 |
| **开发团队** | 阿里巴巴通义实验室 |
| **开源协议** | Apache 2.0 |
| **GitHub Stars** | 核心仓库 22K+，生态 46K+ |

---

## 二、技术架构

### 2.1 三层架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentScope Studio                        │
│              (可视化管控中心 - 智能体仪表盘)                  │
├─────────────────────────────────────────────────────────────┤
│                  AgentScope Runtime                         │
│         (运行时层 - 智能体的"操作系统")                      │
├─────────────────────────────────────────────────────────────┤
│                  AgentScope Core                            │
│         (核心框架层 - 面向智能体开发的"编程语言")            │
└─────────────────────────────────────────────────────────────┘
```

#### 2.1.1 核心框架层（AgentScope Core）

| 组件 | 功能说明 |
|------|---------|
| **MsgHub 消息机制** | 基于消息驱动架构的统一通信路由，支持多模态数据（文本、图像、音频） |
| **模型接口** | 统一接入逻辑，支持 17+ LLM 提供商（通义千问、GPT、Claude、DeepSeek 等） |
| **记忆系统** | 长短时记忆协同机制，短期记忆动态压缩，长期记忆支持关键信息持久化 |
| **工具调用** | 基于 ReAct 范式的工具体系，支持工具分组、元工具动态管理、并行调用 |
| **工作流编排** | 原生支持路由式分发、并行处理、协调者-工作者架构等多种协作模式 |

#### 2.1.2 运行时层（AgentScope Runtime）

| 模块 | 功能 |
|------|------|
| **Engine 模块** | 部署和管理智能体应用的基础设施，内置上下文管理、会话处理、沙箱控制 |
| **Sandbox 模块** | 基于容器化技术的隔离执行环境，严格限制代码执行、文件操作与网络访问权限 |
| **分布式能力** | 基于 Actor 模型实现"中心化编程，分布式运行" |
| **高并发支持** | 内置异步处理框架与实时请求队列，支持批量请求合并处理 |

#### 2.1.3 可视化层（AgentScope Studio）

- **全链路追踪**：基于 OpenTelemetry 标准实现分布式追踪
- **可视化调试**：直观展示智能体思考过程、状态变化与协作轨迹
- **分布式评估**：集成 Ray 分布式计算框架，支持多维度评估指标

### 2.2 核心概念

#### 2.2.1 State（状态管理）

AgentScope 将对象初始化与状态管理分离，支持通过 `load_state_dict` 和 `state_dict` 方法在不同状态间恢复对象。Agent、Memory、Long-term Memory 和 Toolkit 都是有状态对象，支持嵌套状态管理。

#### 2.2.2 Message（消息）

消息是 AgentScope 中的基础数据结构，用于：
- 智能体间信息交换
- 用户界面信息展示
- 记忆存储
- 与不同 LLM API 的统一交互媒介

消息字段：
- `name`: 发送者标识
- `role`: "user", "assistant", "system"
- `content`: 文本或结构化 ContentBlock 对象（支持多模态）
- `metadata`: 额外结构化输出
- 自动生成 `timestamp` 和 `unique id`

#### 2.2.3 Tool（工具）

工具是可调用对象，支持：
- 函数、偏函数、实例方法、类方法、静态方法
- 可调用实例（带 `__call__` 方法）
- 同步/异步、流式/非流式

#### 2.2.4 Agent（智能体）

AgentScope 中智能体行为抽象为三个核心函数：

| 函数 | 用途 |
|------|------|
| `reply()` | 处理传入消息并生成响应消息 |
| `observe()` | 接收环境或其他智能体的消息，不返回响应 |
| `print()` | 将消息显示到目标终端或 Web 界面 |
| `handle_interrupt()` | 处理用户中断（支持实时介入控制） |

ReAct Agent 额外提供：
- `_reasoning()`: 思考并生成工具调用
- `_acting()`: 执行工具函数

---

## 三、技术特性详解

### 3.1 支持的模型

| 提供商 | 支持功能 |
|--------|---------|
| OpenAI | Streaming, Tools, Vision, Reasoning |
| DeepSeek | Streaming, Tools, Vision, Reasoning |
| vLLM | Streaming, Tools, Vision, Reasoning |
| DashScope (通义千问) | Streaming, Tools, Vision, Reasoning |
| Anthropic (Claude) | Streaming, Tools, Vision, Reasoning |
| Gemini | Streaming, Tools, Vision, Reasoning |
| Ollama | Streaming, Tools, Vision, Reasoning |

### 3.2 记忆系统

#### 3.2.1 短期记忆

| 实现 | 用途 |
|------|------|
| `InMemoryMemory` | 存储当前对话上下文、临时任务状态 |
| `RedisMemory` | 分布式环境下的短期记忆 |

#### 3.2.2 长期记忆

| 实现 | 用途 |
|------|------|
| `LongTermMemoryBase` | 持久化上下文：用户偏好、任务历史 |
| `Mem0LongTermMemory` | 基于 Mem0 的长期记忆实现 |

**控制模式**：
- **开发者控制**：`record()`, `retrieve()`
- **智能体自主控制**：`record_to_memory()`, `retrieve_from_memory()`

### 3.3 工具系统

| 能力 | 说明 |
|------|------|
| 工具注册 | 自动从 docstring 生成 JSON schema |
| 工具执行 | 统一异步生成器处理所有工具输出 |
| **MCP 集成** | 支持有状态和无状态客户端 |
| 分组管理 | 动态工具组激活/停用 |

### 3.4 工作流编排模式

#### 3.4.1 Routing（路由模式）

```python
from pydantic import BaseModel, Field
from typing import Literal

class RoutingChoice(BaseModel):
    your_choice: Literal['Content Generation', 'Programming', 'Information Retrieval', None]
    task_description: str = Field(description="任务描述", default=None)

# 路由智能体根据用户查询分配到不同后续任务
routing_agent = ReActAgent(
    name="Routing",
    sys_prompt="你是路由智能体，将用户查询路由到正确的后续任务",
    # ...
)
```

#### 3.4.2 Orchestrator-Workers（编排器-工作者模式）

- 编排器动态创建工作者智能体
- 支持工具调用实现任务分解和分配
- 工作者智能体配备特定工具完成子任务

#### 3.4.3 Handoffs（交接模式）

- 使用状态（如 `active_agent`）在智能体节点之间路由
- 支持"谁拥有对话"的转换

#### 3.4.4 Parallelization（并行化）

- 使用 `asyncio.gather` 实现非阻塞模型调用和并行工具调用
- 通过 Message Hub 实现组通信，向所有注册智能体广播

### 3.5 内置专业智能体

| 智能体 | 用途 | 核心能力 |
|--------|------|---------|
| **Deep Research Agent** | 多源研究和报告生成 | 查询扩展、反思（低级/高级）、摘要、树状工作流 |
| **Browser-use Agent** | 自主网页导航 | 子任务分解、视觉+文本推理、多标签浏览、长网页分块 |
| **Meta Planner** | 复杂多步骤问题解决 | ReAct↔规划模式自动切换、层次化任务分解、动态工作者编排 |

---

## 四、AgentScope Runtime 与 FastAPI 集成

### 4.1 AgentApp 概述

`AgentApp` 是 AgentScope Runtime 提供的**一体化应用服务包装器**，**直接继承自 FastAPI**，提供：

| 特性 | 说明 |
|------|------|
| **完整 FastAPI 生态兼容性** | 支持原生路由注册、中间件扩展、标准生命周期管理 |
| **流式响应 (SSE)** | 实时输出 |
| **任务中断管理** | 基于分布式后端（如 Redis）的任务中断机制 |
| **健康检查端点** | 内置 `/health`, `/readiness`, `/liveness` |
| **可选 Celery 集成** | 异步任务队列 |
| **多种部署目标** | 本地、Kubernetes、函数计算等 |

### 4.2 基础实现示例

```python
from agentscope_runtime.engine import AgentApp
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel

# 创建 AgentApp（继承自 FastAPI）
agent_app = AgentApp(
    app_name="Friday",
    app_description="A helpful assistant",
)

# 使用装饰器注册查询处理器
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    agent = ReActAgent(
        name="Friday",
        model=DashScopeChatModel("qwen-turbo", stream=True),
        # ... 配置
    )
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

# 运行服务
agent_app.run(host="127.0.0.1", port=8090)
```

### 4.3 生命周期管理

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from agentscope.session import RedisSession
from agentscope_runtime.engine import AgentApp

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.state.session = RedisSession(connection_pool=fake_redis.connection_pool)
    print("✅ Service initialized")
    try:
        yield
    finally:
        # 清理阶段
        print("✅ Resources released")

# 传递 lifespan 到 AgentApp
app = AgentApp(
    app_name="Friday",
    app_description="A helpful assistant",
    lifespan=lifespan,
)
```

### 4.4 Celery 异步任务队列

```python
from agentscope_runtime.engine import AgentApp

app = AgentApp(
    agent=agent,
    broker_url="redis://localhost:6379/0",
    backend_url="redis://localhost:6379/0"
)

@app.task("/longjob", queue="celery")
def heavy_computation(data):
    return {"result": data["x"] ** 2}
```

### 4.5 流式输出 (SSE)

```bash
# 客户端示例
curl -N \
  -X POST "http://localhost:8090/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "Hello Friday"}]
    }]
  }'
```

---

## 五、与当前项目对比分析

### 5.1 当前项目技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI + Beanie ODM |
| **数据库** | MongoDB + Motor |
| **任务队列** | Celery + Redis |
| **前端** | React 19 + TypeScript + Vite + TanStack Router/Query |
| **UI 组件** | shadcn/ui + Tailwind CSS v4 |
| **认证** | fastapi-users v15 |

### 5.2 当前 Agent 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                         │
├─────────────────────────────────────────────────────────────┤
│  API Routes (analyses, workflows, agents, ...)             │
├─────────────────────────────────────────────────────────────┤
│  Agent System                                               │
│  ├── BaseAgent (core/agents/base.py)                       │
│  ├── RefinerAgent                                          │
│  ├── ReactAnalyzerAgent                                    │
│  ├── WriterAgent                                           │
│  ├── EditorAgent                                           │
│  ├── ReviewerAgent                                         │
│  ├── OrchestratorAgent                                     │
│  └── FetcherAgent                                          │
├─────────────────────────────────────────────────────────────┤
│  Task System (Celery)                                       │
│  ├── fetch_source_task                                     │
│  ├── fetch_url_and_analyze_task                            │
│  ├── refine_article_task                                   │
│  ├── analyze_article_task                                  │
│  └── rewrite_section_task                                  │
├─────────────────────────────────────────────────────────────┤
│  Workflow System                                            │
│  ├── WorkflowRun (MongoDB)                                 │
│  ├── SSE streaming                                         │
│  └── approve/reject/retry operations                       │
├─────────────────────────────────────────────────────────────┤
│  Models (Beanie ODM)                                        │
│  ├── Article, Source, AgentConfig, WorkflowRun, ...        │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、迁移成本评估

### 6.1 高兼容性领域

| 领域 | 兼容度 | 说明 |
|------|--------|------|
| **FastAPI 基础架构** | ⭐⭐⭐⭐⭐ | AgentApp 直接继承 FastAPI，现有路由可无缝迁移 |
| **MongoDB 数据库** | ⭐⭐⭐⭐ | AgentScope 支持 MongoDB，但需从 Beanie 迁移到 AgentScope 的状态管理 |
| **Celery 任务队列** | ⭐⭐⭐⭐⭐ | AgentScope Runtime 原生支持 Celery，配置方式类似 |
| **Redis** | ⭐⭐⭐⭐⭐ | 用于会话管理和 Celery Broker，完全兼容 |
| **异步架构** | ⭐⭐⭐⭐⭐ | 两者都基于 asyncio，编程模型一致 |

### 6.2 需要重构的领域

| 领域 | 工作量 | 说明 |
|------|--------|------|
| **Agent 基类** | 中等 | 需从自定义 BaseAgent 迁移到 AgentScope 的 AgentBase/ReActAgentBase |
| **消息系统** | 中等 | 需将现有消息格式迁移到 AgentScope 的 Msg 格式 |
| **工作流系统** | 较大 | 现有 WorkflowRun 模型和 SSE 实现需适配 AgentScope 的工作流编排 |
| **记忆系统** | 中等 | 需集成 AgentScope 的 Memory 模块 |
| **工具系统** | 中等 | 现有工具需按 AgentScope 的 Tool 规范重新封装 |
| **前端集成** | 较小 | API 契约可能有变化，需调整前端调用 |

### 6.3 迁移工作量估算

| 模块 | 预估人天 | 复杂度 |
|------|---------|--------|
| 核心 Agent 迁移 | 5-7 天 | 中等 |
| 工作流系统重构 | 7-10 天 | 高 |
| 消息系统适配 | 3-5 天 | 中等 |
| 记忆系统集成 | 3-4 天 | 中等 |
| 工具系统迁移 | 4-6 天 | 中等 |
| API 路由调整 | 2-3 天 | 低 |
| 前端适配 | 3-5 天 | 中等 |
| 测试与验证 | 5-7 天 | 高 |
| **总计** | **32-47 天** | - |

### 6.4 迁移风险

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 功能回归 | 中 | 完善的测试覆盖，渐进式迁移 |
| 性能差异 | 中 | 充分的性能测试和基准对比 |
| 学习曲线 | 中 | 团队培训，文档准备 |
| 社区支持 | 低 | AgentScope 社区活跃，阿里背书 |

---

## 七、迁移优势分析

### 7.1 技术层面优势

| 优势 | 说明 |
|------|------|
| **生产级可靠性** | AgentScope 内置多层容错机制、自动重试、检查点/回滚 |
| **分布式能力** | 原生支持 Actor-based 分布式执行，易于水平扩展 |
| **实时监控** | 内置 AgentScope Studio 可视化调试，无需额外工具 |
| **多模态支持** | 原生支持图像、音频、视频、TTS 等多模态能力 |
| **协议兼容** | 支持 MCP、A2A 等业界标准协议 |
| **记忆管理** | 完善的长短时记忆协同机制 |

### 7.2 开发效率优势

| 优势 | 说明 |
|------|------|
| **工作流编排** | 丰富的内置工作流模式（Routing、Handoffs、Parallelization） |
| **专业智能体** | 开箱即用的 Deep Research、Browser-use、Meta Planner 智能体 |
| **模型无关** | 一次编程，多模型运行，支持 17+ LLM 提供商 |
| **实时介入** | 支持任意时刻安全中断和任务恢复 |

### 7.3 运维层面优势

| 优势 | 说明 |
|------|------|
| **健康检查** | 内置 /health、/readiness、/liveness 探针 |
| **链路追踪** | 基于 OpenTelemetry 的分布式追踪 |
| **K8s 原生** | 支持 Kubernetes 部署，容器化友好 |
| **阿里生态** | 与阿里云百炼平台深度集成 |

### 7.4 长期演进优势

| 优势 | 说明 |
|------|------|
| **社区活跃** | 阿里巴巴持续投入，GitHub 22K+ stars |
| **版本迭代** | 已发布 v1.0 稳定版，API 相对稳定 |
| **企业背书** | 阿里云百炼平台技术基础，生产验证 |

---

## 八、与主流框架对比

### 8.1 AgentScope vs LangChain

| 维度 | AgentScope | LangChain |
|------|-----------|-----------|
| **核心目标** | 生产级多智能体系统 | LLM 应用开发工具包 |
| **抽象级别** | 高级系统平台 | 低级组件库 |
| **多智能体支持** | 原生分布式编排 | 需 LangGraph 扩展 |
| **分布式执行** | ✅ Actor-based | ❌ 单进程为主 |
| **容错机制** | ✅ 内置 | ❌ 需自定义 |
| **监控/仪表板** | ✅ AgentScope Studio | ⚠️ 需 LangSmith（付费） |
| **学习曲线** | 较陡（需运维知识） | 较陡（概念多） |
| **社区规模** | 增长中（22K+ stars） | 庞大（97K+ stars） |
| **生态系统** | 阿里生态 | 最丰富的组件生态 |

### 8.2 AgentScope vs AutoGen

| 维度 | AgentScope | AutoGen |
|------|-----------|---------|
| **通信模型** | 消息传递架构 | 双代理对话协议 |
| **分布式** | ✅ 原生支持 | ⚠️ 复杂，需手动配置 |
| **编程风格** | 单过程式 Python | 复杂执行排序 |
| **容错能力** | ✅ 多层可定制 | 基础 |
| **实时交互** | ✅ 内置中断处理 | ⚠️ 有限支持 |

### 8.3 AgentScope vs CrewAI

| 维度 | AgentScope | CrewAI |
|------|-----------|--------|
| **核心架构** | 三位一体（框架+Runtime+Studio） | 轻量级角色分工 |
| **实时介入** | ✅ 原生支持 | ❌ 不支持 |
| **记忆系统** | 长短时记忆协同 | 简单会话记忆 |
| **分布式** | ✅ 原生支持 | ❌ 不支持 |
| **安全机制** | 容器化沙箱 | 无原生安全 |

---

## 九、迁移建议

### 9.1 推荐迁移策略

**渐进式迁移（推荐）**

```
Phase 1: 试点（2-3 周）
├── 选择非核心工作流进行试点
├── 搭建 AgentScope 基础设施
└── 验证关键能力和性能指标

Phase 2: 并行运行（4-6 周）
├── 新功能使用 AgentScope 开发
├── 现有功能保持运行
└── 逐步迁移高价值工作流

Phase 3: 全面切换（2-3 周）
├── 完成剩余模块迁移
├── 下线旧系统
└── 优化和调优
```

### 9.2 不适合迁移的场景

- 项目即将进入维护期，无新功能开发计划
- 团队资源紧张，无法承担迁移成本
- 当前系统运行稳定，无扩展需求
- 对 LangChain 生态有深度依赖

### 9.3 适合迁移的场景

- 计划扩展多智能体能力
- 有生产级可靠性要求
- 需要分布式部署能力
- 希望降低长期维护成本
- 需要多模态能力支持

---

## 十、结论

### 10.1 总体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **技术成熟度** | ⭐⭐⭐⭐ | v1.0 稳定版，阿里生产验证 |
| **与项目契合度** | ⭐⭐⭐⭐ | 技术栈高度兼容，FastAPI/MongoDB/Celery 均可复用 |
| **迁移成本** | ⭐⭐⭐ | 中等偏高，约 1-2 个月工作量 |
| **长期价值** | ⭐⭐⭐⭐⭐ | 生产级能力、分布式支持、持续演进 |
| **推荐度** | ⭐⭐⭐⭐ | 推荐迁移，但建议渐进式进行 |

### 10.2 最终建议

**建议迁移，但采用渐进式策略：**

1. **短期（1-2 个月）**：保持现有系统稳定运行，同时搭建 AgentScope 基础设施，选择 1-2 个非核心工作流进行试点

2. **中期（3-6 个月）**：新功能优先使用 AgentScope 开发，逐步将高价值工作流迁移到新平台

3. **长期（6-12 个月）**：完成全面迁移，享受 AgentScope 带来的生产级能力和长期演进优势

### 10.3 关键决策点

- 如果项目处于早期阶段或计划大规模扩展多智能体能力 → **强烈建议迁移**
- 如果项目已进入稳定期且资源有限 → **暂缓迁移，保持观察**
- 如果对生产级可靠性和分布式有强需求 → **建议尽快启动迁移**

---

## 参考资料

1. [AgentScope 官方文档](https://doc.agentscope.io/index.html)
2. [AgentScope Runtime 文档](https://runtime.agentscope.io/)
3. [AgentScope GitHub](https://github.com/agentscope-ai/agentscope)
4. [AgentScope: A Flexible yet Robust Multi-Agent Platform (论文)](https://arxiv.org/pdf/2402.14034v1.pdf)
5. [AgentScope 1.0: A Developer-Centric Framework (论文)](https://arxiv.org/pdf/2508.16279)
6. [AgentScope vs LangGraph vs CrewAI 对比](https://www.sotaaz.com/post/agentscope-vs-langgraph-vs-crewai-en)

---

*报告生成时间：2026-04-01*
