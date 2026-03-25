import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class ExternalReference(Document):
    """外部参考文章"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    url: str = Field(..., description="文章链接（唯一）")
    title: str = Field(..., description="文章标题")
    source: str = Field(..., description="来源 (web_search | manual)")
    content: str = Field(default="", description="完整内容（10000字上限）")
    content_snippet: str = Field(default="", description="内容摘要")
    fetched_at: datetime = Field(default_factory=get_datetime_utc, description="获取时间")
    search_query: str = Field(default="", description="搜索关键词")
    metadata: dict = Field(default_factory=dict, description="原始搜索结果元数据")
    referencer_article_ids: list[uuid.UUID] = Field(
        default_factory=list, description="引用该参考的文章ID列表"
    )
    created_at: datetime = Field(default_factory=get_datetime_utc)
    updated_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "external_references"


class ExternalReferenceCreate(BaseModel):
    url: str
    title: str
    source: str = "manual"
    content: str = ""
    content_snippet: str = ""
    search_query: str = ""
    metadata: dict = Field(default_factory=dict)


class ExternalReferenceUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    content_snippet: str | None = None
    metadata: dict | None = None


class ExternalReferencePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    url: str
    title: str
    source: str
    content_snippet: str
    fetched_at: datetime
    search_query: str
    metadata: dict
    referencer_article_ids: list[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class ExternalReferencesPublic(BaseModel):
    data: list[ExternalReferencePublic]
    count: int


class ExternalReferenceDetail(ExternalReferencePublic):
    content: str
