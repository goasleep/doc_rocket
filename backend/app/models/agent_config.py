import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisConfig(BaseModel):
    """分析配置"""
    enable_kb_comparison: bool = Field(default=True, description="是否启用知识库对比")
    enable_web_search: bool = Field(default=True, description="是否启用外部搜索")
    comparison_count: int = Field(default=3, description="对比文章数量")
    analysis_depth: str = Field(default="deep", description="分析深度")


class ReactConfig(BaseModel):
    """React Agent 配置"""
    max_steps: int = Field(default=10, description="最大步骤数")
    reflection_enabled: bool = Field(default=True, description="是否启用反思步骤")
    parallel_analysis: bool = Field(default=True, description="是否并行执行维度分析")


class AgentConfig(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    role: str  # writer | editor | reviewer | orchestrator | analyzer | custom
    responsibilities: str = ""
    system_prompt: str = ""
    model_config_name: str = ""
    is_active: bool = True
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    max_iterations: int = 5
    analysis_config: AnalysisConfig = Field(default_factory=AnalysisConfig, description="分析配置")
    react_config: ReactConfig = Field(default_factory=ReactConfig, description="React Agent 配置")
    created_at: datetime = Field(default_factory=get_datetime_utc)
    updated_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "agent_configs"


class AgentConfigCreate(BaseModel):
    name: str
    role: str
    responsibilities: str = ""
    system_prompt: str = ""
    model_config_name: str = ""
    is_active: bool = True
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    max_iterations: int = 5
    analysis_config: AnalysisConfig = Field(default_factory=AnalysisConfig)
    react_config: ReactConfig = Field(default_factory=ReactConfig)


class AgentConfigUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    responsibilities: str | None = None
    system_prompt: str | None = None
    model_config_name: str | None = None
    is_active: bool | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None
    max_iterations: int | None = None
    analysis_config: AnalysisConfig | None = None
    react_config: ReactConfig | None = None


class AgentConfigPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    role: str
    responsibilities: str
    system_prompt: str
    model_config_name: str
    is_active: bool
    skills: list[str]
    tools: list[str]
    max_iterations: int
    analysis_config: AnalysisConfig
    react_config: ReactConfig
    created_at: datetime
    updated_at: datetime


class AgentConfigsPublic(BaseModel):
    data: list[AgentConfigPublic]
    count: int
