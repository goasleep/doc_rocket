import uuid
from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class PublishHistory(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    draft_id: uuid.UUID
    title: str = ""
    target_platform: Literal["wechat_mp"] = "wechat_mp"
    target_name: str = ""  # 公众号名称
    status: Literal["pending", "success", "failed"] = "pending"
    publish_id: str | None = None  # 微信返回的发布ID
    published_url: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=get_datetime_utc)
    updated_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "publish_histories"


class PublishHistoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    draft_id: uuid.UUID
    title: str
    target_platform: Literal["wechat_mp"]
    target_name: str
    status: Literal["pending", "success", "failed"]
    publish_id: str | None
    published_url: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class PublishHistoriesPublic(BaseModel):
    data: list[PublishHistoryPublic]
    count: int
