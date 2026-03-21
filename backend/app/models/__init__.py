# Re-export existing models for backward compatibility
from app.models.item import (
    Item,
    ItemBase,
    ItemCreate,
    ItemPublic,
    ItemsPublic,
    ItemUpdate,
)
from app.models.user import (
    UpdatePassword,
    User,
    UserCreate,
    UserRead,
    UsersPublic,
    UserUpdate,
)

# New content intelligence models
from app.models.agent_config import (
    AgentConfig,
    AgentConfigCreate,
    AgentConfigPublic,
    AgentConfigsPublic,
    AgentConfigUpdate,
)
from app.models.analysis import (
    AnalysesPublic,
    ArticleAnalysis,
    ArticleAnalysisPublic,
    ArticleStructure,
    ArticleStyle,
    QualityBreakdown,
)
from app.models.article import (
    Article,
    ArticleCreate,
    ArticleDetail,
    ArticlePublic,
    ArticlesPublic,
)
from app.models.draft import (
    Draft,
    DraftPublic,
    DraftsPublic,
    DraftUpdate,
    EditHistoryEntry,
    RewriteSectionRequest,
    RewriteSectionResponse,
)
from app.models.source import (
    ApiConfig,
    FetchConfig,
    Source,
    SourceCreate,
    SourcePublic,
    SourcesPublic,
    SourceUpdate,
)
from app.models.tool import (
    Tool,
    ToolPublic,
    ToolsPublic,
    ToolUpdate,
)
from app.models.skill import (
    Skill,
    SkillCreate,
    SkillPublic,
    SkillScript,
    SkillsPublic,
    SkillUpdate,
)
from app.models.system_config import (
    LLMProviderConfig,
    LLMProviderPublic,
    LLMProvidersConfig,
    LLMProvidersPublic,
    ModelDefaults,
    OrchestratorConfig,
    SchedulerConfig,
    SearchConfig,
    SystemConfig,
    SystemConfigPublic,
    SystemConfigUpdate,
)
from app.models.workflow import (
    AgentStep,
    RoutingEvent,
    WorkflowApprove,
    WorkflowInput,
    WorkflowReject,
    WorkflowRun,
    WorkflowRunCreate,
    WorkflowRunPublic,
    WorkflowRunsPublic,
)

# Generic
from pydantic import BaseModel


class Message(BaseModel):
    message: str


__all__ = [
    # User
    "User", "UserRead", "UserCreate", "UserUpdate", "UpdatePassword", "UsersPublic",
    # Item
    "Item", "ItemBase", "ItemCreate", "ItemUpdate", "ItemPublic", "ItemsPublic",
    # Source
    "Source", "SourceCreate", "SourceUpdate", "SourcePublic", "SourcesPublic",
    "ApiConfig", "FetchConfig",
    # Article
    "Article", "ArticleCreate", "ArticlePublic", "ArticleDetail", "ArticlesPublic",
    # Analysis
    "ArticleAnalysis", "ArticleAnalysisPublic", "AnalysesPublic",
    "QualityBreakdown", "ArticleStructure", "ArticleStyle",
    # AgentConfig
    "AgentConfig", "AgentConfigCreate", "AgentConfigUpdate",
    "AgentConfigPublic", "AgentConfigsPublic",
    # Workflow
    "WorkflowRun", "WorkflowRunCreate", "WorkflowRunPublic", "WorkflowRunsPublic",
    "AgentStep", "RoutingEvent", "WorkflowInput", "WorkflowApprove", "WorkflowReject",
    # Draft
    "Draft", "DraftPublic", "DraftsPublic", "DraftUpdate", "EditHistoryEntry",
    "RewriteSectionRequest", "RewriteSectionResponse",
    # SystemConfig
    "SystemConfig", "SystemConfigPublic", "SystemConfigUpdate",
    "LLMProviderConfig", "LLMProviderPublic", "LLMProvidersConfig", "LLMProvidersPublic",
    "SchedulerConfig", "ModelDefaults", "SearchConfig", "OrchestratorConfig",
    # Skill
    "Skill", "SkillCreate", "SkillUpdate", "SkillPublic", "SkillsPublic", "SkillScript",
    # Tool
    "Tool", "ToolUpdate", "ToolPublic", "ToolsPublic",
    # Generic
    "Message",
]
