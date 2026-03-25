## Overview

React Agent 模式的文章分析引擎，通过多步骤推理、工具调用、对比分析生成高质量文章分析报告。

## Requirements

### Functional Requirements

#### REQ-001: 多步骤分析流程
ReactAnalyzerAgent 必须执行以下步骤：
1. **理解文章**: 提取主题、核心观点、目标受众、文章类型
2. **知识库对比**: 搜索相似主题的历史文章，获取其分析数据
3. **外部搜索**: 搜索同类热门文章，获取参考内容
4. **并行维度分析**: 同时分析内容深度、可读性、原创性、传播潜力
5. **综合评分**: 基于评分标准为每个维度打分，附带详细解释
6. **反思验证**: 检查评分一致性，生成最终报告

#### REQ-002: 工具调用支持
Agent 必须支持以下工具：
- `search_similar_articles`: 搜索知识库相似文章
- `web_search`: 外部网络搜索
- `fetch_url`: 获取参考文章内容
- `save_external_reference`: 保存外部参考文章
- `compare_with_reference`: 对比文章差异

#### REQ-003: 过程追溯
每步必须记录到 trace 数组：
- step_index: 步骤序号
- step_name: 步骤名称
- step_type: thought/tool_call/observation/conclusion/reflection
- input_summary/output_summary: 输入输出摘要
- tool_calls: 工具调用详情
- duration_ms: 耗时
- parallel_group/parallel_index: 并行组标识（维度分析步骤）

#### REQ-004: 配置驱动
通过 AgentConfig.analysis_config 配置：
- enable_kb_comparison: 是否启用知识库对比
- enable_web_search: 是否启用外部搜索（有 Tavily key 默认 true）
- comparison_count: 对比文章数量
- analysis_depth: 当前固定为 "deep"

### Non-Functional Requirements

#### REQ-005: 性能
- 完整分析流程应在 30 秒内完成
- 维度分析步骤并行执行

#### REQ-006: 可靠性
- 工具调用失败时记录错误，继续后续步骤
- 每个步骤设置超时控制

## API

### Input
```python
{
  "article_content": str,      # 文章内容
  "article_id": UUID           # 文章ID
}
```

### Output
```python
{
  "quality_score": float,
  "quality_breakdown": QualityBreakdown,
  "quality_score_details": list[QualityScoreDetail],
  "comparison_references": list[ComparisonReferenceEmbedded],
  "analysis_summary": str,
  "improvement_suggestions": list[str],
  "trace": list[AnalysisTraceStep],
  # ... 其他原有字段
}
```
