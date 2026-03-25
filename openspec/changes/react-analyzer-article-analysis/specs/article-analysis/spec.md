## Overview

文章分析功能扩展，新增评分详情、对比参考、改进建议、多步骤追溯。

## Requirements

### Functional Requirements

#### REQ-001: 评分详情 (QualityScoreDetail)
每个维度评分必须包含：
- dimension: 维度名称
- score: 分数 0-100
- weight: 权重
- weighted_score: 加权分数
- reasoning: 评分依据说明
- standard_matched: 符合的评分档位描述
- evidences: 支撑证据列表（引用原文）
- improvement_suggestions: 改进建议列表

#### REQ-002: 对比参考 (ComparisonReference)
分析结果必须包含引用的对比文章：
- 知识库文章引用：article_id, title, quality_score
- 外部参考引用：external_ref_id, url, title
- 共同字段：source, similarity_score, key_differences, learnings, advantages

#### REQ-003: 分析摘要
- analysis_summary: 整体分析总结（200字内）
- improvement_suggestions: 聚合所有维度的改进建议

#### REQ-004: 多步骤追溯 (AnalysisTraceStep)
trace 数组必须包含所有分析步骤：
- 理解文章、知识库对比、外部搜索
- 4个并行维度分析步骤（带 parallel_group 标识）
- 综合评分、反思验证

#### REQ-005: API 扩展
- `GET /analyses/{article_id}`: 响应包含新增字段
- `GET /analyses/{article_id}/trace`: 获取详细追溯

### Data Model Changes

```python
class ArticleAnalysis(Document):
    # 原有字段保留...

    # 新增字段
    quality_score_details: list[QualityScoreDetail]
    comparison_references: list[ComparisonReferenceEmbedded]
    analysis_summary: str
    improvement_suggestions: list[str]
    trace: list[AnalysisTraceStep]  # 扩展结构
    rubric_version: str
    analysis_duration_ms: int

class QualityScoreDetail(BaseModel):
    dimension: str
    score: float
    weight: float
    weighted_score: float
    reasoning: str
    standard_matched: str
    evidences: list[ScoreEvidence]
    improvement_suggestions: list[str]

class ComparisonReferenceEmbedded(BaseModel):
    source: str  # knowledge_base | external
    # KB fields
    kb_article_id: UUID | None
    kb_article_title: str | None
    # External fields
    external_ref_id: UUID | None
    external_url: str | None
    external_title: str | None
    # Common
    quality_score: float | None
    similarity_score: float
    key_differences: list[str]
    learnings: list[str]
    advantages: list[str]

class AnalysisTraceStep(BaseModel):
    step_index: int
    step_name: str
    step_type: str
    input_summary: str
    output_summary: str
    tool_calls: list[ToolCallDetail]
    raw_response: str
    duration_ms: int
    timestamp: datetime
    parsed_ok: bool
    parallel_group: str | None  # 新增
    parallel_index: int | None  # 新增
```

### Frontend Components

- `QualityScoreDetailCard`: 评分详情展示
- `ComparisonReferenceCard`: 对比参考展示
- `AnalysisTraceTimeline`: 过程追溯时间线
- `AnalysisSummarySection`: 分析摘要和改进建议

## Backward Compatibility

- 新字段均有默认值，旧数据兼容
- API 响应新增字段，不影响现有前端
- 支持重新分析更新旧数据
