import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


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
    hook_type: str = ""
    framework: str = ""  # AIDA / PAS / story etc.
    emotional_triggers: list[str] = Field(default_factory=list)
    key_phrases: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    structure: ArticleStructure = Field(default_factory=ArticleStructure)
    style: ArticleStyle = Field(default_factory=ArticleStyle)
    target_audience: str = ""
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "article_analyses"


class ArticleAnalysisPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    article_id: uuid.UUID
    quality_score: float
    quality_breakdown: QualityBreakdown
    hook_type: str
    framework: str
    emotional_triggers: list[str]
    key_phrases: list[str]
    keywords: list[str]
    structure: ArticleStructure
    style: ArticleStyle
    target_audience: str
    created_at: datetime


class AnalysesPublic(BaseModel):
    data: list[ArticleAnalysisPublic]
    count: int
