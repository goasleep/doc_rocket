"""Token usage tracking models for LLM consumption monitoring."""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class TokenUsage(Document):
    """Records a single LLM call's token consumption."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    agent_config_id: Optional[uuid.UUID] = None
    agent_config_name: str = ""
    model_name: str = ""
    entity_type: str = ""  # "article" | "workflow" | "task" | "draft"
    entity_id: Optional[uuid.UUID] = None
    operation: str = ""  # "refine" | "analyze" | "rewrite" | "chat"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    usage_missing: bool = False  # True if API didn't return usage data
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "token_usages"
        indexes = [
            [("agent_config_id", 1), ("created_at", -1)],
            [("entity_type", 1), ("entity_id", 1), ("created_at", -1)],
            [("model_name", 1), ("created_at", -1)],
            [("created_at", -1)],
        ]


class TokenUsageDaily(Document):
    """Aggregated daily token consumption by agent and model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    date: Indexed(datetime)  # type: ignore[valid-type]
    agent_config_id: Optional[uuid.UUID] = None
    agent_config_name: str = ""
    model_name: str = ""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    updated_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "token_usage_daily"
        indexes = [
            [("date", -1), ("agent_config_id", 1)],
            [("date", -1), ("model_name", 1)],
            [("agent_config_id", 1), ("date", -1)],
        ]


# Pydantic schemas for API responses


class TokenUsagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_config_id: Optional[uuid.UUID]
    agent_config_name: str
    model_name: str
    entity_type: str
    entity_id: Optional[uuid.UUID]
    operation: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime


class TokenUsageDailyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: datetime
    agent_config_id: Optional[uuid.UUID]
    agent_config_name: str
    model_name: str
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    call_count: int


class TokenUsageCreate(BaseModel):
    agent_config_id: Optional[uuid.UUID] = None
    agent_config_name: str = ""
    model_name: str = ""
    entity_type: str = ""
    entity_id: Optional[uuid.UUID] = None
    operation: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    usage_missing: bool = False


class AgentTokenStats(BaseModel):
    """Aggregated token stats for an agent."""

    agent_config_id: Optional[uuid.UUID]
    agent_config_name: str
    model_name: str
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    call_count: int


class ArticleTokenUsage(BaseModel):
    """Token usage breakdown for a specific article."""

    operation: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime


class ArticleTokenUsageSummary(BaseModel):
    """Summary of all token usage for an article."""

    article_id: uuid.UUID
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    operation_count: int
    operations: list[ArticleTokenUsage]
