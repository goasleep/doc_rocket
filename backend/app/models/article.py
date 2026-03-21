import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class Article(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_id: uuid.UUID | None = None
    title: str
    content: str
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    status: str = "raw"  # raw | analyzing | analyzed | archived
    input_type: str = "fetched"  # fetched | manual
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "articles"


class ArticleCreate(BaseModel):
    title: str
    content: str
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    source_id: uuid.UUID | None = None
    input_type: str = "manual"


class ArticlePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_id: uuid.UUID | None
    title: str
    url: str | None
    author: str | None
    published_at: datetime | None
    status: str
    input_type: str
    created_at: datetime
    quality_score: float | None = None  # joined from ArticleAnalysis


class ArticleDetail(ArticlePublic):
    content: str
    analysis: dict | None = None  # embedded ArticleAnalysis data


class ArticlesPublic(BaseModel):
    data: list[ArticlePublic]
    count: int
