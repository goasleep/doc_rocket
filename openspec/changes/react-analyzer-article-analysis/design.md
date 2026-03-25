## Context

当前文章分析系统使用简单的单步 LLM 调用，分析结果缺乏深度和可解释性。用户反馈评分主观、没有对比依据、无法追溯分析过程。需要引入 React Agent 模式，通过多步骤推理、工具调用、对比分析来提升分析质量。

## Goals / Non-Goals

**Goals:**
- 实现 React Agent 模式的多步骤文章分析
- 提供明确的评分标准，每个分数都有详细解释和证据
- 支持知识库文章对比和外部文章搜索对比
- 完整的过程追溯，每步可见
- 外部参考文章管理，支持双向关联

**Non-Goals:**
- 向量搜索（当前使用关键词+LLM相关性判断）
- 实时分析（保持异步任务模式）
- 多语言评分标准（先实现内容导向的通用标准）
- 自动改进文章（只提供分析，不自动修改）

## Decisions

### 1. 完全替换 AnalyzerAgent
**决策**: 移除现有单步 AnalyzerAgent，只保留 ReactAnalyzerAgent
**理由**: 简化维护，统一分析体验，避免用户困惑
**替代方案**: 并存 quick/standard/deep 模式（被拒绝）

### 2. 外部参考文章单独存储
**决策**: 创建 ExternalReference 集合，与 ArticleAnalysis 双向关联
**理由**: 避免重复抓取，支持多文章引用同一参考，可追溯引用关系
**结构**: ExternalReference 存完整内容（10000字上限），ArticleAnalysis 嵌入引用摘要

### 3. 评分标准版本管理
**决策**: 系统只维护一个 is_active=true 的评分标准
**理由**: 简化逻辑，确保分析一致性
**更新方式**: 创建新版本 → 切换 active 状态

### 4. web_search 默认行为
**决策**: 有 Tavily API key 默认开启，没有则关闭
**理由**: 无缝体验，无需额外配置
**实现**: 检查 SystemConfig.search.tavily_api_key

### 5. 并行分析步骤表示
**决策**: trace 中拆分为 4 个独立步骤，加 parallel_group 标识
**理由**: 既展示并行关系，又保持 trace 数组结构简单

### 6. 旧数据兼容
**决策**: 新字段设默认值，支持重新分析更新
**理由**: 避免强制迁移，给用户控制权
**实现**: quality_score_details=[], comparison_references=[] 等默认值

## Risks / Trade-offs

**分析时间较长** → 并行执行 4 个维度分析优化；前端实时展示 trace 步骤减少等待感

**外部搜索成本** → Tavily API 调用限制；可通过 enable_web_search 关闭

**LLM 调用次数多** → 单次分析约 8-10 次 LLM 调用；使用缓存和重试机制

**外部参考内容失效** → 保存 content_snippet 作为快照；支持重新抓取

**评分标准主观性** → 明确评分档位标准；支持版本迭代优化

## Migration Plan

1. **部署前**: 创建 QualityRubric v1 标准数据
2. **部署**: 新代码上线，新旧 Agent 切换无感知
3. **数据**: 旧分析数据兼容，新字段使用默认值
4. **回滚**: 回滚代码即可，数据库新字段不影响旧代码

## Open Questions

- 评分标准 v1 的具体档位描述需要内容专家确认
- Tavily API 的 rate limit 是否需要请求节流
