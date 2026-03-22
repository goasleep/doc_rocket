import uuid
from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class LLMModelConfig(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str  # unique display name / identifier used by agents
    provider_type: Literal["openai_compatible", "kimi"] = "kimi"
    base_url: str | None = None  # for openai_compatible; kimi uses hardcoded URL
    api_key_encrypted: str | None = None
    model_id: str  # actual model name passed to the API
    is_active: bool = True
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "llm_model_configs"


class LLMModelConfigCreate(BaseModel):
    name: str
    provider_type: Literal["openai_compatible", "kimi"] = "kimi"
    base_url: str | None = None
    api_key: str | None = None
    model_id: str
    is_active: bool = True


class LLMModelConfigUpdate(BaseModel):
    name: str | None = None
    provider_type: Literal["openai_compatible", "kimi"] | None = None
    base_url: str | None = None
    api_key: str | None = None
    model_id: str | None = None
    is_active: bool | None = None


class LLMModelConfigPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    provider_type: str
    base_url: str | None
    api_key_masked: str | None
    model_id: str
    is_active: bool
    created_at: datetime


class LLMModelConfigsPublic(BaseModel):
    data: list[LLMModelConfigPublic]
    count: int
