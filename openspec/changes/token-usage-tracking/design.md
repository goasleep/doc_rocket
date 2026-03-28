## Context

当前系统的 LLM 调用通过 `OpenAICompatibleClient` 和 `BaseAgent` 进行，但响应中不包含 Token 使用量信息。MongoDB 已作为数据库使用（Beanie ODM）。需要在不破坏现有接口的前提下，扩展 LLM 客户端返回 Token 使用量，并在 Agent 层自动记录。

## Goals / Non-Goals

**Goals:**
- 记录每次 LLM 调用的 Token 消耗（prompt/completion/total）
- 支持按 Agent、模型、日期维度聚合查询
- 支持按文章维度查询 Token 消耗明细
- 前端展示 Agent 今日/昨日 Token 消耗统计
- 前端展示单篇文章的各阶段 Token 消耗明细
- **前端提供交互式图表展示 Token 趋势和分布（折线图、饼图、柱状图）**
- 提供完整的单元测试、集成测试和 E2E 测试

**Non-Goals:**
- 实时 Token 消耗预警/告警
- 基于 Token 消耗的成本预测
- 多租户/多用户的 Token 配额限制
- 非 OpenAI 兼容的 LLM 提供商（如纯 Claude SDK）的 Token 追踪

## Decisions

### 1. Token 记录位置：在 LLM Client 返回后、Agent 中记录
**Rationale**:
- 在 `OpenAICompatibleClient.chat()` 中从 API 响应提取 usage 信息
- 在 `BaseAgent.run()` 中统一记录，避免每个子类重复实现
- 通过 `context` 参数传递关联实体信息（article_id, operation 等）

**Alternative considered**:
- 在 LLM Client 内部直接写入数据库 → 拒绝：Client 应保持纯净，不涉及业务逻辑
- 通过中间件/装饰器自动记录 → 拒绝：增加复杂度，当前调用链路简单直接

### 2. 数据模型：原始记录 + 日聚合双表设计
**Rationale**:
- `TokenUsage`: 记录每次调用的原始数据，支持明细查询
- `TokenUsageDaily`: 按天预聚合，支持快速统计查询（今日/昨日/趋势）
- 使用 MongoDB 的复合索引优化查询性能

**Schema**:
```python
TokenUsage:
  - agent_config_id: UUID | None
  - agent_config_name: str
  - model_name: str
  - entity_type: str  # "article" | "workflow" | "task"
  - entity_id: UUID
  - operation: str    # "refine" | "analyze" | "rewrite"
  - prompt_tokens: int
  - completion_tokens: int
  - total_tokens: int
  - created_at: datetime

TokenUsageDaily:
  - date: date
  - agent_config_id: UUID | None
  - model_name: str
  - total_prompt_tokens: int
  - total_completion_tokens: int
  - total_tokens: int
  - call_count: int
```

### 3. 聚合策略：写入时实时更新 + 定时任务兜底
**Rationale**:
- 每次记录 TokenUsage 后，同步更新/创建对应的 TokenUsageDaily 记录
- 避免定时任务延迟导致的统计不准确
- 定时任务仅用于数据修复和一致性校验

### 4. 前端展示位置
**Rationale**:
- Agent 列表页：显示今日/昨日 Token 消耗卡片 → 运营人员快速了解成本
- Agent 列表页：显示 7/30/90 天趋势折线图 → 了解 Token 消耗趋势
- Agent 列表页：显示 Agent 对比柱状图 → 比较不同 Agent 的消耗
- 文章详情页：显示精修、分析各阶段的 Token 消耗 → 了解单篇文章成本
- 文章详情页：显示操作分布饼图 → 直观了解各阶段占比
- 使用现有 TanStack Query 进行数据获取和缓存

### 5. 图表库选择：Recharts
**Rationale**:
- Recharts 是 React 生态中最流行的图表库，API 设计符合 React 思维
- 基于 D3.js，支持响应式、动画、交互式 tooltip
- 与 Tailwind CSS 和 shadcn/ui 设计系统容易集成
- 支持折线图（趋势）、柱状图（对比）、饼图（分布）等常用图表类型
- 包体积适中（~70kb gzipped），支持 tree-shaking

**Alternative considered**:
- Chart.js + react-chartjs-2 → 功能强大但配置较繁琐，React 集成不如 Recharts 自然
- Victory → 学习曲线较陡，社区相对较小
- 自研 SVG 图表 → 拒绝：维护成本高，交互功能实现复杂

### 6. 测试策略
**Rationale**:
- 单元测试：模型验证、服务逻辑（使用内存 MongoDB）
- 集成测试：API 端点（使用 TestClient + 内存 MongoDB）
- E2E 测试：使用 Playwright + Chrome DevTools 验证前端展示

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Token 记录增加 LLM 调用延迟 | 使用 Fire-and-forget 异步写入，不阻塞主流程 |
| 高频写入导致 MongoDB 压力 | 批量写入优化（后续迭代）、适当索引、分片准备 |
| 数据量过大影响查询性能 | 原始数据 TTL 策略（保留 90 天）、日聚合永久保留 |
| API 响应中无 usage 字段 | 降级处理：记录为 0 并标记 `usage_missing=True` |
| 并发更新日聚合导致冲突 | 使用 MongoDB upsert + $inc 原子操作 |

## Migration Plan

1. **数据库**: 无需迁移，新集合自动创建
2. **索引**: 应用启动时 Beanie 自动创建
3. **部署步骤**:
   - 部署后端代码
   - 验证 TokenUsage 记录正常写入
   - 部署前端代码
   - 验证展示正常
4. **Rollback**: 回滚代码即可，新集合不影响现有功能

## Open Questions

1. 是否需要记录预估成本（基于模型单价计算 USD）？
2. 原始 TokenUsage 数据保留多久？建议 90 天后归档或删除
3. 是否需要支持按用户维度的 Token 统计？
