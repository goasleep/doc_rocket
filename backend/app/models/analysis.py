import uuid
from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class ToolCallDetail(BaseModel):
    """工具调用详情"""
    tool_name: str
    input_params: dict = Field(default_factory=dict)
    output_summary: str = ""
    success: bool = True
    error_message: str = ""


class AnalysisTraceStep(BaseModel):
    """分析追溯步骤"""
    step_index: int
    step_name: str = Field(default="", description="步骤名称")
    step_type: str = Field(default="", description="步骤类型 (thought/tool_call/observation/conclusion/reflection)")
    input_summary: str = Field(default="", description="输入摘要")
    output_summary: str = Field(default="", description="输出摘要")
    messages_sent: list[Any] = Field(default_factory=list)
    raw_response: str = ""
    parsed_ok: bool = True
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=get_datetime_utc)
    tool_calls: list[ToolCallDetail] = Field(default_factory=list, description="工具调用详情")
    parallel_group: str | None = Field(default=None, description="并行组标识")
    parallel_index: int | None = Field(default=None, description="并行组内索引")


class ScoreEvidence(BaseModel):
    """评分证据"""
    quote: str = Field(..., description="原文引用")
    context: str = Field(default="", description="上下文说明")


class QualityScoreDetail(BaseModel):
    """维度评分详情"""
    dimension: str = Field(..., description="维度名称")
    score: float = Field(..., ge=0, le=100, description="分数 0-100")
    weight: float = Field(..., ge=0, le=1, description="权重")
    weighted_score: float = Field(..., description="加权分数")
    reasoning: str = Field(default="", description="评分依据说明")
    standard_matched: str = Field(default="", description="符合的评分档位描述")
    evidences: list[ScoreEvidence] = Field(default_factory=list, description="支撑证据列表")
    improvement_suggestions: list[str] = Field(default_factory=list, description="改进建议列表")


class ComparisonReferenceEmbedded(BaseModel):
    """嵌入的对比参考"""
    source: str = Field(..., description="来源 (knowledge_base | external)")
    # 知识库文章字段
    kb_article_id: uuid.UUID | None = Field(default=None, description="知识库文章ID")
    kb_article_title: str | None = Field(default=None, description="知识库文章标题")
    # 外部参考字段
    external_ref_id: uuid.UUID | None = Field(default=None, description="外部参考ID")
    external_url: str | None = Field(default=None, description="外部文章URL")
    external_title: str | None = Field(default=None, description="外部文章标题")
    # 共同字段
    quality_score: float | None = Field(default=None, description="质量分数")
    similarity_score: float = Field(default=0.0, description="相似度分数")
    key_differences: list[str] = Field(default_factory=list, description="关键差异")
    learnings: list[str] = Field(default_factory=list, description="可借鉴之处")
    advantages: list[str] = Field(default_factory=list, description="对方优势")


class QualityBreakdown(BaseModel):
    content_depth: float = 0.0
    readability: float = 0.0
    originality: float = 0.0
    virality_potential: float = 0.0


class ArticleStructure(BaseModel):
    intro: str = ""
    body_sections: list[str] = Field(default_factory=list)
    cta: str = ""


class ArticleStyle(BaseModel):
    tone: str = ""
    formality: str = ""
    avg_sentence_length: float = 0.0


class ArticleAnalysis(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    article_id: uuid.UUID
    quality_score: float = 0.0
    quality_breakdown: QualityBreakdown = Field(default_factory=QualityBreakdown)
    # 新增字段
    quality_score_details: list[QualityScoreDetail] = Field(
        default_factory=list, description="维度评分详情"
    )
    comparison_references: list[ComparisonReferenceEmbedded] = Field(
        default_factory=list, description="对比参考"
    )
    analysis_summary: str = Field(default="", description="分析摘要")
    improvement_suggestions: list[str] = Field(default_factory=list, description="改进建议")
    rubric_version: str = Field(default="", description="评分标准版本")
    analysis_duration_ms: int = Field(default=0, description="分析耗时(毫秒)")
    # 原有字段
    hook_type: str = ""
    framework: str = ""  # AIDA / PAS / story etc.
    emotional_triggers: list[str] = Field(default_factory=list)
    key_phrases: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    structure: ArticleStructure = Field(default_factory=ArticleStructure)
    style: ArticleStyle = Field(default_factory=ArticleStyle)
    target_audience: str = ""
    topic: str = ""  # 文章主题
    article_type: str = ""  # 文章类型 (news/opinion/tutorial/story/review/other)
    trace: list[AnalysisTraceStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "article_analyses"


class ArticleAnalysisPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    article_id: uuid.UUID
    quality_score: float
    quality_breakdown: QualityBreakdown
    # 新增字段
    quality_score_details: list[QualityScoreDetail]
    comparison_references: list[ComparisonReferenceEmbedded]
    analysis_summary: str
    improvement_suggestions: list[str]
    rubric_version: str
    analysis_duration_ms: int
    # 原有字段
    hook_type: str
    framework: str
    emotional_triggers: list[str]
    key_phrases: list[str]
    keywords: list[str]
    structure: ArticleStructure
    style: ArticleStyle
    target_audience: str
    topic: str
    article_type: str
    trace: list[AnalysisTraceStep]
    created_at: datetime


class AnalysesPublic(BaseModel):
    data: list[ArticleAnalysisPublic]
    count: int
