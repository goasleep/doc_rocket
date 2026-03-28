## Why

当前系统缺乏对 LLM Token 消耗的精细化追踪能力。运营团队无法准确了解每个 Agent、每篇文章、每次操作的 Token 消耗情况，导致无法优化成本、评估模型效率或进行准确的费用分摊。需要建立完整的 Token 消耗追踪体系，支持按 Agent、按文章、按时间维度的统计和查询。

## What Changes

- **新增 TokenUsage 数据模型**：记录每次 LLM 调用的 Token 消耗（prompt/completion/total）、模型名称、Agent 信息、关联实体（文章/工作流）
- **新增 TokenUsageDaily 聚合模型**：按天汇总各 Agent 和模型的 Token 消耗，支持快速查询今日/昨日/历史趋势
- **扩展 LLM Client**：在 `ChatResponse` 中增加 usage 字段，所有 LLM 客户端返回 Token 使用量
- **扩展 BaseAgent**：在每次 LLM 调用后自动记录 Token 消耗，支持通过 context 传递关联实体信息
- **新增 Token Usage Service**：封装 Token 记录、聚合、查询业务逻辑
- **新增 REST API**：提供 Agent 维度、文章维度的 Token 消耗查询接口
- **前端展示**：在 Agent 管理页面显示今日/昨日 Token 消耗卡片、7/30/90 天趋势折线图、Agent 对比柱状图；在文章详情页显示该文章的总 Token 消耗、各阶段明细列表、操作分布饼图

## Capabilities

### New Capabilities
- `token-usage-tracking`: Token 消耗追踪核心功能，包括数据模型、服务层、API 层
- `token-usage-frontend`: 前端 Token 消耗展示组件和数据可视化

### Modified Capabilities
- `llm-abstraction`: 扩展 LLM 客户端接口，在响应中返回 Token 使用量
- `agent-config`: Agent 执行时自动记录 Token 消耗，需要传递上下文信息

## Impact

- **后端**: 新增 2 个 Beanie Document 模型、1 个 Service 类、1 个 API Router
- **数据库**: 新增 `token_usages` 和 `token_usage_daily` 集合，需要创建复合索引优化查询
- **前端**: 新增 TokenUsage 展示组件和图表组件（使用 recharts 或 chart.js），修改 Agent 列表页和文章详情页
- **API**: 新增 `/api/v1/token-usage/*` 端点
- **测试**: 需要单元测试（模型、服务）、集成测试（API）、E2E 测试（前端展示）
- **部署**: 无需额外基础设施，使用现有 MongoDB
