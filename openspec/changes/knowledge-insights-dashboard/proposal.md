## Why

当前平台积累了大量文章及其 AI 分析数据，但运营者和内容创作者缺乏一个高维度的俯瞰视角来理解知识库的整体特征。用户无法快速回答"我们的内容在讨论什么主题"、"最常见的情绪触发是什么"、"内容质量短板在哪里"等问题。一个可视化的洞察仪表板能够将分散的单篇文章分析聚合成可行动的群体洞察，直接提升内容策略的决策效率。

## What Changes

- 新增 `InsightSnapshot` 数据模型，用于存储预聚合的知识库洞察快照（全局 scope）。
- 扩展 `ArticleAnalysis` 模型，新增 `topic`（主题）和 `article_type`（文章类型）字段。
- 修改 `ReactAnalyzerAgent`，使其在分析流程中提取并返回 `topic` 和 `article_type`。
- 新增后端聚合服务 `InsightSnapshotService`，从全库分析结果中批量生成关键词云、情绪触发词云、写作框架分布、钩子类型分布、改进建议聚合、主题分布、质量分分布等快照数据。
- 新增 `insights` API 路由：
  - `GET /insights/snapshot/latest` — 获取最新快照
  - `GET /insights/snapshot` — 获取快照历史列表
  - `POST /insights/snapshot/refresh` — 手动触发快照生成（202 Accepted）
- 新增 Celery 定时任务 `insight_snapshot_task`，通过 redbeat 调度每日自动刷新全局快照。
- 新增前端页面 `/insights`（路由名待定），使用 ECharts + echarts-wordcloud 展示：
  - 关键词云（支持按平均质量分着色）
  - 情绪触发词云
  - 写作框架分布图（饼图/环形图）
  - 钩子类型分布图
  - 改进建议词云（按维度可切换）
  - 主题分布图
  - 质量分分布直方图
  - 顶部概览指标卡片（总文章数、已分析数、平均质量分）
  - 手动刷新按钮 + 生成时间显示
- 前端安装新依赖：`echarts`、`echarts-for-react`、`echarts-wordcloud`。

## Capabilities

### New Capabilities
- `knowledge-insights`: 知识库洞察快照的生成、存储、查询与可视化展示。
- `insight-refresh-api`: 手动与定时触发洞察快照刷新的后端 API。

### Modified Capabilities
- `article-analysis`: 分析模型和 Agent 输出新增 `topic` 和 `article_type` 字段，用于支撑主题分布洞察。仅对新分析文章生效，存量数据为空。

## Impact

- **后端 API**: 新增 `/api/v1/insights/*` 路由；`api/main.py` 注册新模块。
- **数据库**: MongoDB 新增 `insight_snapshots` collection；`article_analyses` 文档新增字段。
- **定时任务**: redbeat 新增 `insight_snapshot_global` 调度条目。
- **前端**: 新增 `frontend/src/routes/_layout/insights.tsx` 及配套组件目录；`package.json` 新增 ECharts 依赖。
- **Agent**: `react_analyzer.py` 的 `run()` 返回值和 LLM prompt 轻微调整。
