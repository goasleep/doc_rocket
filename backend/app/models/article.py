import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class ArticleImage(BaseModel):
    """Image extracted from article content."""
    original_url: str
    qiniu_url: str
    alt: str = ""


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
    content_md: str | None = None
    refine_status: str = "pending"
    created_at: datetime = Field(default_factory=get_datetime_utc)
    # Images extracted from article content
    images: list[ArticleImage] = Field(default_factory=list)
    # Original HTML content (extracted main content only)
    raw_html: str | None = None

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
    images: list[ArticleImage] = Field(default_factory=list)


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
    refine_status: str
    created_at: datetime
    quality_score: float | None = None  # joined from ArticleAnalysis
    images: list[ArticleImage] = Field(default_factory=list)


class ArticleDetail(ArticlePublic):
    content: str
    content_md: str | None = None
    refine_status: str
    analysis: dict | None = None  # embedded ArticleAnalysis data
    images: list[ArticleImage] = Field(default_factory=list)
    raw_html: str | None = None


class ArticlesPublic(BaseModel):
    data: list[ArticlePublic]
    count: int
