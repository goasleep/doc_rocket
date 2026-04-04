import uuid
from datetime import UTC, datetime

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


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
    pass


class OrchestratorConfig(BaseModel):
    enabled: bool = False


class WordCloudFilterConfig(BaseModel):
    """词云关键词过滤配置"""
    excluded_keywords: list[str] = Field(default_factory=list, description="需要过滤的关键词列表")
    min_keyword_length: int = Field(default=2, description="最小关键词长度")
    max_keyword_count: int = Field(default=100, description="词云最大关键词数量")


class WechatMPConfig(BaseModel):
    """微信公众号配置"""
    app_id: str = ""
    app_secret_encrypted: str | None = None
    enabled: bool = False


class SystemConfig(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    llm_providers: LLMProvidersConfig = Field(default_factory=LLMProvidersConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    analysis: ModelDefaults = Field(default_factory=ModelDefaults)
    writing: ModelDefaults = Field(default_factory=ModelDefaults)
    search: SearchConfig = Field(default_factory=SearchConfig)
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    word_cloud_filter: WordCloudFilterConfig = Field(default_factory=WordCloudFilterConfig)
    wechat_mp: WechatMPConfig = Field(default_factory=WechatMPConfig)
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


class WechatMPConfigPublic(BaseModel):
    """微信公众号公开配置（app_secret 脱敏）"""
    model_config = ConfigDict(from_attributes=True)
    app_id: str
    app_secret_masked: str | None = None
    enabled: bool


class SystemConfigPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    llm_providers: LLMProvidersPublic
    scheduler: SchedulerConfig
    analysis: ModelDefaults
    writing: ModelDefaults
    search: SearchConfig
    orchestrator: OrchestratorConfig
    word_cloud_filter: WordCloudFilterConfig
    wechat_mp: WechatMPConfigPublic


class SystemConfigUpdate(BaseModel):
    kimi_api_key: str | None = None
    claude_api_key: str | None = None
    openai_api_key: str | None = None
    scheduler: SchedulerConfig | None = None
    analysis: ModelDefaults | None = None
    writing: ModelDefaults | None = None
    search: SearchConfig | None = None
    orchestrator: OrchestratorConfig | None = None
    word_cloud_filter: WordCloudFilterConfig | None = None
    wechat_mp: WechatMPConfig | None = None
