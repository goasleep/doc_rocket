import uuid
from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class ApiConfig(BaseModel):
    items_path: str  # e.g. "data.items"
    title_field: str
    content_field: str
    url_field: str
    author_field: str | None = None
    published_at_field: str | None = None


class FetchConfig(BaseModel):
    interval_minutes: int = 60
    max_items_per_fetch: int = 20


class Source(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(min_length=1, max_length=255)
    type: str  # "api" | "rss"
    url: str
    api_key: str | None = None
    headers: dict[str, str] | None = None
    api_config: ApiConfig | None = None  # required for API type; None for RSS
    fetch_config: FetchConfig = Field(default_factory=FetchConfig)
    is_active: bool = True
    last_fetched_at: datetime | None = None
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "sources"


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str
    url: str
    api_key: str | None = None
    headers: dict[str, Any] | None = None
    api_config: ApiConfig | None = None
    fetch_config: FetchConfig = Field(default_factory=FetchConfig)
    is_active: bool = True


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    api_key: str | None = None
    headers: dict[str, Any] | None = None
    api_config: ApiConfig | None = None
    fetch_config: FetchConfig | None = None
    is_active: bool | None = None


class SourcePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    type: str
    url: str
    api_config: ApiConfig | None
    fetch_config: FetchConfig
    is_active: bool
    last_fetched_at: datetime | None
    created_at: datetime


class SourcesPublic(BaseModel):
    data: list[SourcePublic]
    count: int
