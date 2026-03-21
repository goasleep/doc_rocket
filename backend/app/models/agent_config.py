import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class AgentConfig(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    role: str  # writer | editor | reviewer | custom
    responsibilities: str = ""
    system_prompt: str = ""
    model_provider: str = "kimi"  # kimi | claude | openai
    model_id: str = "moonshot-v1-32k"
    workflow_order: int = 1
    is_active: bool = True
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "agent_configs"


class AgentConfigCreate(BaseModel):
    name: str
    role: str
    responsibilities: str = ""
    system_prompt: str = ""
    model_provider: str = "kimi"
    model_id: str = "moonshot-v1-32k"
    workflow_order: int = 1
    is_active: bool = True


class AgentConfigUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    responsibilities: str | None = None
    system_prompt: str | None = None
    model_provider: str | None = None
    model_id: str | None = None
    workflow_order: int | None = None
    is_active: bool | None = None


class AgentConfigPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    role: str
    responsibilities: str
    system_prompt: str
    model_provider: str
    model_id: str
    workflow_order: int
    is_active: bool
    created_at: datetime


class AgentConfigsPublic(BaseModel):
    data: list[AgentConfigPublic]
    count: int
