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
from app.models.llm_model_config import (
    LLMModelConfig,
    LLMModelConfigCreate,
    LLMModelConfigPublic,
    LLMModelConfigsPublic,
    LLMModelConfigUpdate,
)
from app.models.agent_config import (
    AgentConfig,
    AgentConfigCreate,
    AgentConfigPublic,
    AgentConfigsPublic,
    AgentConfigUpdate,
    AnalysisConfig,
    ReactConfig,
)
from app.models.analysis import (
    AnalysesPublic,
    AnalysisTraceStep,
    ArticleAnalysis,
    ArticleAnalysisPublic,
    ArticleStructure,
    ArticleStyle,
    ComparisonReferenceEmbedded,
    QualityBreakdown,
    QualityScoreDetail,
    ScoreEvidence,
    ToolCallDetail,
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
    WordCloudFilterConfig,
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
from app.models.task_run import (
    TaskRun,
    TaskRunPublic,
    TaskRunsPublic,
)
from app.models.quality_rubric import (
    QualityRubric,
    QualityRubricCreate,
    QualityRubricPublic,
    QualityRubricsPublic,
    QualityRubricUpdate,
    RubricCriterion,
    RubricDimension,
    DEFAULT_RUBRIC_V1,
)
from app.models.external_reference import (
    ExternalReference,
    ExternalReferenceCreate,
    ExternalReferencePublic,
    ExternalReferencesPublic,
    ExternalReferenceUpdate,
    ExternalReferenceDetail,
)
from app.models.transcript import (
    Transcript,
)
from app.models.task_graph import (
    TaskNode,
)
from app.models.token_usage import (
    AgentTokenStats,
    ArticleTokenUsage,
    ArticleTokenUsageSummary,
    TokenUsage,
    TokenUsageCreate,
    TokenUsageDaily,
    TokenUsageDailyPublic,
    TokenUsagePublic,
)
from app.models.insight_snapshot import (
    DistributionItem,
    InsightSnapshot,
    InsightSnapshotMeta,
    InsightSnapshotOverview,
    InsightSnapshotPublic,
    InsightSnapshotsPublic,
    QualityScoreBucket,
    RefreshSnapshotResponse,
    SuggestionDimensionItem,
    WordCloudItem,
)
from app.models.publish_history import (
    PublishHistory,
    PublishHistoriesPublic,
    PublishHistoryPublic,
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
    "AnalysisTraceStep", "ToolCallDetail",
    "QualityBreakdown", "ArticleStructure", "ArticleStyle",
    "QualityScoreDetail", "ScoreEvidence", "ComparisonReferenceEmbedded",
    # LLMModelConfig
    "LLMModelConfig", "LLMModelConfigCreate", "LLMModelConfigUpdate",
    "LLMModelConfigPublic", "LLMModelConfigsPublic",
    # AgentConfig
    "AgentConfig", "AgentConfigCreate", "AgentConfigUpdate",
    "AgentConfigPublic", "AgentConfigsPublic",
    "AnalysisConfig", "ReactConfig",
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
    "WordCloudFilterConfig",
    # Skill
    "Skill", "SkillCreate", "SkillUpdate", "SkillPublic", "SkillsPublic", "SkillScript",
    # Tool
    "Tool", "ToolUpdate", "ToolPublic", "ToolsPublic",
    # TaskRun
    "TaskRun", "TaskRunPublic", "TaskRunsPublic",
    # QualityRubric
    "QualityRubric", "QualityRubricCreate", "QualityRubricUpdate",
    "QualityRubricPublic", "QualityRubricsPublic",
    "RubricCriterion", "RubricDimension", "DEFAULT_RUBRIC_V1",
    # ExternalReference
    "ExternalReference", "ExternalReferenceCreate", "ExternalReferenceUpdate",
    "ExternalReferencePublic", "ExternalReferencesPublic", "ExternalReferenceDetail",
    # Transcript
    "Transcript",
    # Task Graph
    "TaskNode",
    # Token Usage
    "TokenUsage", "TokenUsageCreate", "TokenUsagePublic",
    "TokenUsageDaily", "TokenUsageDailyPublic",
    "AgentTokenStats", "ArticleTokenUsage", "ArticleTokenUsageSummary",
    # Insight Snapshot
    "InsightSnapshot", "InsightSnapshotPublic", "InsightSnapshotsPublic",
    "InsightSnapshotMeta", "InsightSnapshotOverview",
    "WordCloudItem", "DistributionItem", "SuggestionDimensionItem",
    "QualityScoreBucket", "RefreshSnapshotResponse",
    # Publish History
    "PublishHistory", "PublishHistoryPublic", "PublishHistoriesPublic",
    # Generic
    "Message",
]
