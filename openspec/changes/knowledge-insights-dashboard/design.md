## Context

平台已有文章库（`Article` + `ArticleAnalysis`）和基于 Beanie + MongoDB 的后端架构。单篇文章的分析结果在文章详情页展示，但缺少将全库分析结果聚合为群体洞察的能力。本设计旨在通过"快照模式"解决大规模聚合查询的性能问题，同时保持前端交互的轻量和实时感。

## Goals / Non-Goals

**Goals:**
- 提供预聚合的知识库洞察数据，支持词云、分布图、趋势概览等可视化。
- 快照生成由后端负责，前端仅做纯展示，避免每次打开页面全库扫描。
- 支持自动每日刷新 + 手动即时刷新两种更新机制。
- 保留快照历史，默认展示最新，前端可查看生成时间。

**Non-Goals:**
- 不做实时级联更新（文章新增/分析完成不会立即触发快照更新）。
- 不做按来源(scope=source_id)或多维度的分片快照（先支持全局 scope）。
- 不对存量文章做 topic 回填（仅对新分析生效）。
- 不在本期实现快照版本间的 diff 对比 UI（历史列表只展示元信息）。

## Decisions

### 1. 快照模型独立存储 vs 实时聚合
**选择**：独立 `InsightSnapshot` Document 存储预聚合结果。
**理由**：MongoDB 上实时聚合大量数组字段（`keywords`、`emotional_triggers`）效率低且前端体验差。快照模式一次计算、多次读取，天然适合缓存和分页历史。

### 2. 定时任务用 redbeat 而非静态 beat schedule
**选择**：通过 redbeat 在任务首次加载或系统启动时注册 `insight_snapshot_global` 条目。
**理由**：现有 `sources.py` 已使用 redbeat 做动态调度，保持一致性。同时 redbeat 支持运行时启用/禁用，比 `celerybeat-schedule` 文件更可靠。

### 3. 改进建议聚合策略：按维度分组 + 关键词频次
**选择**：不做 LLM 语义聚类，而是将 `quality_score_details` 中的 `improvement_suggestions` 按 `dimension` 分组，再提取 suggestion 文本中的高频关键词。
**理由**：LLM 聚类成本高、不稳定；按维度分组能直接对应业务 actionable 方向（如"内容深度不足"），关键词频次则提供词云所需的数据结构。

### 4. 词云库用 ECharts + echarts-wordcloud
**选择**：前端引入 `echarts`、`echarts-for-react`、`echarts-wordcloud`。
**理由**：ECharts 生态功能最全，词云支持颜色映射、形状、交互事件。虽然包体积增加，但 dashboard 页面是唯一使用方，影响可控。

### 5. topic / article_type 只对新分析生效
**选择**：修改 `react_analyzer.py` 的 LLM prompt 和 `run()` 返回值，将 `topic` 和 `article_type` 写入 `ArticleAnalysis`，但不回填存量。
**理由**：存量数据需要重新分析或写一次性脚本才能补全，成本高。新字段设为可选，对现有业务零破坏。

### 6. 并发控制用 TaskRun  vs Redis 锁
**选择**：用 `TaskRun` 记录快照生成任务状态（`pending` / `running` / `done` / `failed`），`POST /insights/snapshot/refresh` 时检查是否存在 `running` 状态的任务，存在则返回 429 Too Many Requests。
**理由**：`TaskRun`  already 是平台统一的任务追踪机制，复用它能保持可观测性，无需引入额外的 Redis 锁逻辑。

### 7. 快照批量聚合的分页策略
**选择**：`InsightSnapshotService.generate()` 使用 `skip/limit` 分批拉取 `ArticleAnalysis`，每批 500 条，在 Python 内存中做 Counter 聚合。
**理由**：500 条是一个在内存占用和查询次数之间的平衡点。`ArticleAnalysis` 的文档大小适中，批量读取不会给 Motor/Event Loop 带来明显压力。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 文章数量增长后，快照生成耗时变长 | 1) 分页批量读取；2) 未来可将 scope 拆分为 source 级别并行生成；3) 必要时将高频聚合改到 MongoDB Aggregation Pipeline。 |
| `echarts-wordcloud` 对 React 19 兼容性存疑 | 先安装验证最小 demo，若有问题则降级为基于 `ref` 的直接 ECharts 封装，不依赖 `echarts-for-react`。 |
| 改进建议关键词提取过于粗糙 | 第一期用简单分词（去除停用词）+ 频次统计；第二期若业务反馈不足，再增加 LLM 主题聚类 Agent。 |
| 用户频繁点击手动刷新导致重复计算 | `TaskRun` 运行中状态拦截 + 前端按钮 loading 态，双重保护。 |
| 快照数据和实际数据存在时间差 | 页面明确展示"数据生成于 xxx"，降低用户对实时性的预期。 |

## Migration Plan

1. **代码部署**：新模型和 API 随常规部署上线，对现有接口无影响。
2. **定时任务激活**：部署后首次启动时，redbeat 条目自动创建（由系统初始化逻辑或首次请求触发）。
3. **依赖安装**：前端 `pnpm install` 安装 ECharts 相关包。
4. **OpenAPI 客户端更新**：后端 API 上线后执行 `pnpm run generate-client`。
5. **无数据回滚需求**：此功能为纯新增，回滚时删除 `insight_snapshots` collection 即可。

## Open Questions

- `insights` 页面在 Sidebar 中的入口位置和图标（待前端开发时确定）。
- 是否需要为快照生成任务失败时发送通知（如系统内通知或日志告警）——建议先只记录 `TaskRun.error_message`。
