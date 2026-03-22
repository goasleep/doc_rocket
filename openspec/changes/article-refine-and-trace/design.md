## Context

当前 fetch/RSS 拉取到的文章以原始纯文本或残缺 HTML 存储在 `Article.content`。`AnalyzerAgent` 直接使用该字段，LLM 面对格式混乱的输入，分析质量不稳定。分析过程只保留最终结构化结果，发生解析失败或质量异常时无原始 LLM 响应可查。

已有基础设施：
- `BaseAgent` / `AgentConfig` 提供 LLM 配置
- `TaskRun` 统一记录任务执行状态（`task_type` 枚举扩展即可）
- `@uiw/react-md-editor` 已安装，`MDEditor.Markdown` 可直接用于只读渲染
- 文章详情页已有 `Tabs` 组件和「任务历史」时间线

## Goals / Non-Goals

**Goals:**
- 在 fetch 到 analyze 之间插入精修步骤，产出 `content_md`
- 精修失败时降级，不中断分析流程
- `AnalyzerAgent` 优先使用 `content_md`，同时记录完整 trace
- 前端可查看精修版 Markdown 和分析过程 trace

**Non-Goals:**
- 不对已有历史文章批量补跑精修（仅新增/重新抓取的文章走新流程）
- 不支持用户手动编辑 `content_md`
- 不为精修过程做 trace（RefinerAgent 是单次调用，价值有限）

## Decisions

### 1. 精修作为独立 Celery 任务，而非内嵌在 fetch 任务中

fetch 任务已承担网络请求、去重、TaskRun 创建等职责，将精修嵌入会使 fetch 任务超时风险上升，且精修失败会导致整个 fetch 任务失败。独立任务隔离失败域，并可被「重新触发精修」单独使用。

### 2. 精修完成后由 refine_article_task 直接入队 analyze（而非 analyze 轮询等待）

方案对比：
| 方案 | 优点 | 缺点 |
|------|------|------|
| refine 完成后入队 analyze | 无轮询、延迟低 | refine.py 需 import analyze task |
| analyze 任务开头检查 refine_status | 解耦 | 需要轮询或延迟重试机制 |
| Celery chord/chain | 原生支持 | 引入 chord 复杂度，现有代码不用 |

选择方案一：简单直接，与现有 fetch → analyze 链路模式一致（fetch.py 也直接 import analyze task）。

### 3. trace 嵌入 ArticleAnalysis，而非独立集合

trace 的生命周期与分析结果完全一致：重新分析时，旧分析删除，trace 跟着消失，新 trace 随新分析写入。独立集合会引入孤儿 trace 清理问题。单次 LLM 调用的 trace 体积约 2-5KB，不会造成文档膨胀。

### 4. refine_status 作为 Article 独立字段，而非复用 status

`Article.status`（raw/analyzing/analyzed/archived）反映分析流程状态，与精修正交。若合并状态机，会产生 `refining`、`refine_failed` 等状态，与 `analyzing` 互相干扰，UI 逻辑复杂化。分离后，前端可独立显示精修和分析的进度。

### 5. `ArticlePublic` 和 `ArticleDetail` 均暴露 `content_md` 和 `refine_status`

`ArticlePublic`（列表）需要 `refine_status` 以便列表页显示精修状态角标。`ArticleDetail` 需要 `content_md` 用于精修版 Tab 渲染。

## Risks / Trade-offs

- **精修增加端到端延迟**：fetch → refine → analyze 串行，比原来多一次 LLM 调用。缓解：refine 用较快的模型（可通过 agent_config 配置），且 refine 与 analyze 是不同 task，用户在 TaskRun 时间线上可见各步骤进度。

- **精修 LLM 输出不稳定**：若 LLM 未严格遵循"不扩写"指令，可能修改原意。缓解：prompt 中明确禁止扩写，仅做格式整理；analyze 仍使用 `content_md` 但分析结果问题可通过 trace 溯源。

- **已有文章无 content_md**：`content_md=None` 时前端精修版 Tab 显示等待状态，不影响分析结果查看；历史文章触发「重新抓取」后会走新流程。

## Migration Plan

1. 部署后端：新字段 `content_md`、`refine_status` 为可选，Beanie 自动兼容旧文档（字段缺失时取默认值）
2. 部署前端：新 Tab 和 trace 区域降级优雅（`content_md=None` → 显示提示，`trace=[]` → 不渲染追溯区域）
3. 无需数据迁移，无需停机

## Implementation Notes

### re-analysis（POST /analyses/）不经过 refine
用户手动触发重新分析时，直接入队 `analyze_article_task`，跳过 refine 步骤。这是故意的：已有 `content_md` 继续使用，无 `content_md` 则降级用原文。重新分析不会触发重新精修，也不会修改 `refine_status`。

### submit.py text mode 同样需要更新
`api/routes/submit.py` 的 text mode 直接调 `analyze_article_task`，需改为先入队 `refine_article_task`，与 fetch 流程保持一致。

### `ArticlePublic`（列表）只加 `refine_status`，不加 `content_md`
已有规范要求列表响应不返回 `content` 字段。`content_md` 同样可能较大，遵循相同原则，仅在 `ArticleDetail`（详情）中暴露。列表页展示精修状态角标只需要 `refine_status`。

## Open Questions

- 精修任务是否需要支持手动触发（前端「重新精修」按钮）？当前设计仅在 fetch/refetch 时自动触发。可作为后续迭代。
