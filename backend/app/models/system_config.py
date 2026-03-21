import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class LLMProviderConfig(BaseModel):
    api_key_encrypted: str | None = None
    default_model: str = ""


class LLMProvidersConfig(BaseModel):
    kimi: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(default_model="moonshot-v1-32k"))
    claude: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(default_model="claude-sonnet-4-6"))
    openai: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(default_model="gpt-4o"))


class SchedulerConfig(BaseModel):
    default_interval_minutes: int = 60
    max_concurrent_fetches: int = 3


class ModelDefaults(BaseModel):
    default_model_provider: str = "kimi"
    default_model_id: str = "moonshot-v1-32k"


class SearchConfig(BaseModel):
    tavily_api_key: str = ""


class OrchestratorConfig(BaseModel):
    enabled: bool = False


class SystemConfig(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    llm_providers: LLMProvidersConfig = Field(default_factory=LLMProvidersConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    analysis: ModelDefaults = Field(default_factory=ModelDefaults)
    writing: ModelDefaults = Field(default_factory=ModelDefaults)
    search: SearchConfig = Field(default_factory=SearchConfig)
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "system_config"


class LLMProviderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """API key is masked in responses."""
    api_key_masked: str | None = None
    default_model: str


class LLMProvidersPublic(BaseModel):
    kimi: LLMProviderPublic
    claude: LLMProviderPublic
    openai: LLMProviderPublic


class SystemConfigPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    llm_providers: LLMProvidersPublic
    scheduler: SchedulerConfig
    analysis: ModelDefaults
    writing: ModelDefaults
    search: SearchConfig
    orchestrator: OrchestratorConfig


class SystemConfigUpdate(BaseModel):
    kimi_api_key: str | None = None
    claude_api_key: str | None = None
    openai_api_key: str | None = None
    scheduler: SchedulerConfig | None = None
    analysis: ModelDefaults | None = None
    writing: ModelDefaults | None = None
    search: SearchConfig | None = None
    orchestrator: OrchestratorConfig | None = None
