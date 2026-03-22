## 1. 数据模型扩展

- [x] 1.1 在 `models/article.py` 的 `Article` 上新增 `content_md: str | None = None` 和 `refine_status: str = "pending"` 字段
- [x] 1.2 在 `models/article.py` 的 `ArticlePublic`（列表）上新增 `refine_status: str` 字段（不加 `content_md`，列表响应不应包含大字段）
- [x] 1.3 在 `models/article.py` 的 `ArticleDetail` 上新增 `content_md: str | None` 和 `refine_status: str` 字段
- [x] 1.4 在 `models/analysis.py` 新增 `AnalysisTraceStep(BaseModel)`，包含 `step_index`、`messages_sent`、`raw_response`、`parsed_ok`、`duration_ms`、`timestamp` 字段
- [x] 1.5 在 `models/analysis.py` 的 `ArticleAnalysis` 上新增 `trace: list[AnalysisTraceStep]` 字段（默认空列表）
- [x] 1.6 在 `models/analysis.py` 的 `ArticleAnalysisPublic` 上新增 `trace: list[AnalysisTraceStep]` 字段

## 2. RefinerAgent

- [x] 2.1 新建 `backend/app/core/agents/refiner.py`，继承 `BaseAgent`，实现 `run(input_text: str) -> str` 方法
- [x] 2.2 设计针对中文科技内容的 system prompt：清除噪声（导航栏、广告、版权声明）、恢复标题层级/段落/列表/代码块结构、输出纯 Markdown、禁止扩写删减
- [x] 2.3 使用 `llm.chat()` 发起调用，直接返回 LLM 原始文本（非 JSON 模式）

## 3. refine_article_task

- [x] 3.1 新建 `backend/app/tasks/refine.py`，实现 `_refine_article_async(article_id, task_run_id)` 异步函数
- [x] 3.2 任务开头更新 `Article.refine_status="refining"` 和 `TaskRun.status="running"`
- [x] 3.3 调用 `RefinerAgent.run(article.content)`，将结果写入 `Article.content_md`，设置 `refine_status="refined"`
- [x] 3.4 精修成功后：创建 analyze TaskRun（从 refine TaskRun 复制 `triggered_by` 和 `triggered_by_label`），然后调用 `analyze_article_task.apply_async(args=[article_id], kwargs={"task_run_id": ...}, task_id=f"analyze_{article_id}")`
- [x] 3.5 精修失败时：设置 `refine_status="failed"`，TaskRun 标为 `failed`；同样创建 analyze TaskRun（复制 `triggered_by`/`triggered_by_label`），调用 `analyze_article_task.apply_async(task_id=f"analyze_{article_id}")` 降级入队（analyze task 会自行使用 `article.content_md or article.content`，此时 `content_md=None` 故降级为原文）
- [x] 3.6 注册 `@celery_app.task(name="refine_article_task")` 装饰器（`task_id` 不在装饰器上配置，由各调用方在 `apply_async(..., task_id=f"refine_{article_id}")` 处设置）

## 4. 修改 fetch 任务链

- [x] 4.1 在 `tasks/fetch.py` 的 `_fetch_source_async` 中，将 `analyze_article_task` 入队替换为 `refine_article_task` 入队（创建 refine TaskRun，使用 `task_id=f"refine_{article_id}"`）
- [x] 4.2 在 `tasks/fetch.py` 的 `_fetch_url_and_analyze_async` 中做同样替换
- [x] 4.3 在 `tasks/fetch.py` 的 `_refetch_article_async` 中做同样替换，同时重置 `Article.refine_status="pending"` 并清空 `Article.content_md=None`

## 5. 修改 submit 路由

- [x] 5.1 在 `api/routes/submit.py` 的 text mode（第 70 行）中，将 `analyze_article_task.apply_async()` 替换为 `refine_article_task.apply_async()`（创建 refine TaskRun，`task_id=f"refine_{article_id}"`）
- [x] 5.2 URL mode 通过 `fetch_url_and_analyze_task` → `_fetch_url_and_analyze_async` 已在任务 4.2 中覆盖，无需额外修改

## 6. 修改 AnalyzerAgent

- [x] 6.1 在 `tasks/analyze.py` 的 `_analyze_article_async` 中，将传给 `agent.run()` 的内容改为 `article.content_md or article.content`
- [x] 6.2 在 `core/agents/analyzer.py` 的 `run()` 方法中，记录 LLM 调用前后时间戳，计算 `duration_ms`
- [x] 6.3 `run()` 返回 dict 中新增 `trace` 键，值为包含一个**原始 dict** 的列表，字段为 `step_index`、`messages_sent`、`raw_response`、`parsed_ok`、`duration_ms`、`timestamp`（不在 agent 层 import models，保持 core/agents 与 models 的单向依赖）
- [x] 6.4 在 `tasks/analyze.py` 中，从 `analysis_data` pop 出 `trace`（原始 dict 列表），构造 `[AnalysisTraceStep(**s) for s in trace]`，写入 `ArticleAnalysis.trace`；其余字段通过 `**analysis_data` 展开

## 7. 前端：精修版 Tab

- [x] 7.1 在 `articles/$id.tsx` 的 Tabs 中新增「精修版」Tab（FileText 图标），顺序为：`分析结果 | 精修版 | 任务历史`（原文内容 Card 仍留在「分析结果」Tab 内，不变为独立 Tab）
- [x] 7.2 Tab 内容：`content_md` 存在时使用 `MDEditor.Markdown` 组件渲染
- [x] 7.3 Tab 内容：`refine_status` 为 "pending"/"refining" 时显示等待提示；为 "failed" 时显示精修失败提示（说明已降级使用原文分析）

## 8. 前端：分析过程追溯

- [x] 8.1 在「分析结果」Tab 的 `AnalysisCards` 下方新增可折叠的「分析过程追溯」区域（使用 `useState` 控制展开/收起）
- [x] 8.2 仅当 `analysis.trace` 非空时渲染该区域
- [x] 8.3 渲染每个 `AnalysisTraceStep`：显示 `step_index`、`duration_ms`、`parsed_ok` 状态 badge
- [x] 8.4 `messages_sent` 按 role 分块显示（system/user/assistant）；`raw_response` 用 monospace 代码块显示

## 9. 测试

- [x] 9.1 新建 `tests/unit/agents/test_refiner_agent.py`：mock LLM，验证 `RefinerAgent.run()` 返回非空字符串；验证超长内容被截断后仍正常调用
- [x] 9.2 新建 `tests/tasks/test_refine_task.py`：
  - 成功路径：mock `RefinerAgent._get_llm` 返回 mock LLM，验证 `Article.content_md` 被写入、`refine_status="refined"`、`analyze_article_task.apply_async` 被调用一次
  - 失败降级路径：`patch("app.core.agents.refiner.RefinerAgent.run", side_effect=RuntimeError("llm error"))`，验证 `refine_status="failed"`、`analyze_article_task.apply_async` 仍被调用
  - TaskRun 状态正确流转（pending → running → done/failed）
- [x] 9.3 更新 `tests/tasks/test_analyze_task.py`：
  - 新增用例：`article.content_md` 非空时，LLM 收到的是 `content_md` 而非 `content`
  - 新增用例：`article.content_md` 为 None 时，LLM 收到 `content`（降级）
  - 新增用例：`ArticleAnalysis.trace` 包含一个 `AnalysisTraceStep`，字段完整（`messages_sent` 非空，`raw_response` 非空，`duration_ms > 0`）
- [x] 9.4 更新 `tests/tasks/test_fetch_task.py`：
  - 更新现有用例：fetch 后入队的是 `refine_article_task` 而非 `analyze_article_task`
  - 新增用例：refetch 时 `Article.content_md` 被清空，`refine_status` 重置为 "pending"

## 10. API Client 与收尾

- [x] 10.1 运行 `bash scripts/generate-client.sh` 重新生成前端 API 客户端
- [x] 10.2 确认 `ArticlePublic`（含 `refine_status`）、`ArticleDetail`（含 `content_md`、`refine_status`）、`ArticleAnalysisPublic`（含 `trace`）的新字段已出现在生成的客户端类型中
- [x] 10.3 确认 `models/__init__.py` 导出了 `AnalysisTraceStep`（如需要）
