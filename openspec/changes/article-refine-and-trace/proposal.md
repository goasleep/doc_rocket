## Why

fetch/RSS 拉取到的文章内容质量参差不齐（纯文本、残缺 HTML、格式混乱），直接送入 LLM 分析效果不佳；同时分析过程完全黑盒，出问题时无法追溯 LLM 实际发送了什么、收到了什么原始响应。

## What Changes

- 新增 `RefinerAgent`：专为中文科技内容设计，将爬取的原始文本整理为规范 Markdown，保留核心内容、清除噪声
- 新增 `refine_article_task` Celery 任务：接入 TaskRun 系统，精修成功后自动入队 analyze，精修失败则降级使用原文直接入队 analyze
- 修改 fetch 任务链：fetch → refine → analyze（替换原有的 fetch → analyze）
- 修改 `AnalyzerAgent`：优先使用 `content_md`，记录完整 trace（messages、原始响应、耗时、解析状态）
- `Article` 新增 `content_md`、`refine_status` 字段
- `ArticleAnalysis` 新增 `trace` 字段（嵌入式，生命周期与分析结果一致）
- 前端文章详情页新增「精修版」Tab，使用已有 `MDEditor.Markdown` 渲染
- 前端分析结果 Tab 新增可折叠「分析过程追溯」区域

## Capabilities

### New Capabilities

- `article-refinement`: RefinerAgent 精修流程——Article 模型扩展、refine_article_task、任务链变更、前端精修版 Tab
- `analysis-trace`: 分析过程追溯——AnalysisTraceStep 模型、AnalyzerAgent trace 记录、前端追溯展示区域

### Modified Capabilities

- `article-ingestion`: fetch 任务链由 fetch→analyze 改为 fetch→refine→analyze；Article 新增 `content_md`、`refine_status` 字段
- `article-analysis`: AnalyzerAgent 优先使用 `content_md`；ArticleAnalysis 新增 `trace` 字段；API schema 暴露 trace

## Impact

- **Backend**：新增 `core/agents/refiner.py`、`tasks/refine.py`；修改 `tasks/fetch.py`（三处入队逻辑）、`tasks/analyze.py`（content_md 优先）、`core/agents/analyzer.py`（trace 记录）、`models/article.py`、`models/analysis.py`、`models/__init__.py`
- **数据库**：`articles` collection 新增 `content_md`、`refine_status` 字段；`article_analyses` collection 新增 `trace` 字段
- **前端**：`routes/_layout/articles/$id.tsx` 新增精修版 Tab 及追溯区域；重新生成 API 客户端
- **TaskRun**：新增 `task_type="refine"`，接入现有任务历史时间线
