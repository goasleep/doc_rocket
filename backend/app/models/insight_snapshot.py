"""InsightSnapshot model — pre-aggregated knowledge base analytics."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class WordCloudItem(BaseModel):
    """词云数据项"""
    name: str  # 词/关键词
    value: int  # 频次
    avg_score: float  # 包含该词的文章平均质量分


class DistributionItem(BaseModel):
    """分布图数据项"""
    name: str  # 类别名称
    value: int  # 数量


class SuggestionDimensionItem(BaseModel):
    """改进建议按维度分组的数据"""
    dimension: str  # 维度名称
    keywords: list[WordCloudItem]  # 该维度下的高频关键词


class QualityScoreBucket(BaseModel):
    """质量分数分布桶"""
    range: str  # 分数范围，如 "0-20", "21-40" 等
    count: int  # 该范围内的文章数量


class InsightSnapshotOverview(BaseModel):
    """概览指标"""
    total_articles: int  # 文章总数
    analyzed_count: int  # 已分析文章数
    avg_quality_score: float  # 平均质量分
    coverage_rate: float  # 分析覆盖率 (analyzed_count / total_articles)


class InsightSnapshot(Document):
    """知识库洞察快照 - 预聚合的全局分析数据"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    scope: Literal["global"] = "global"  # 当前仅支持全局快照

    # 概览指标
    overview: InsightSnapshotOverview

    # 词云数据
    keyword_cloud: list[WordCloudItem] = Field(default_factory=list)
    emotional_trigger_cloud: list[WordCloudItem] = Field(default_factory=list)

    # 分布数据
    framework_distribution: list[DistributionItem] = Field(default_factory=list)
    hook_type_distribution: list[DistributionItem] = Field(default_factory=list)
    topic_distribution: list[DistributionItem] = Field(default_factory=list)

    # AI味道分布
    ai_flavor_distribution: list[QualityScoreBucket] = Field(default_factory=list, description="AI味道分数分布")

    # 改进建议聚合
    suggestion_aggregation: list[SuggestionDimensionItem] = Field(default_factory=list)

    # 质量分数分布（直方图）
    quality_score_distribution: list[QualityScoreBucket] = Field(default_factory=list)

    # 统计信息
    article_count: int = 0  # 参与聚合的文章数
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "insight_snapshots"


class InsightSnapshotPublic(BaseModel):
    """快照公开模型"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scope: Literal["global"]
    overview: InsightSnapshotOverview
    keyword_cloud: list[WordCloudItem]
    emotional_trigger_cloud: list[WordCloudItem]
    framework_distribution: list[DistributionItem]
    hook_type_distribution: list[DistributionItem]
    topic_distribution: list[DistributionItem]
    ai_flavor_distribution: list[QualityScoreBucket]
    suggestion_aggregation: list[SuggestionDimensionItem]
    quality_score_distribution: list[QualityScoreBucket]
    article_count: int
    created_at: datetime


class InsightSnapshotMeta(BaseModel):
    """快照元信息（用于历史列表）"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scope: Literal["global"]
    article_count: int
    created_at: datetime


class InsightSnapshotsPublic(BaseModel):
    """快照列表响应"""
    data: list[InsightSnapshotMeta]
    count: int


class RefreshSnapshotResponse(BaseModel):
    """手动刷新响应"""
    task_run_id: uuid.UUID
    message: str
