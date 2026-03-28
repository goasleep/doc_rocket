import uuid
from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class RoutingEvent(BaseModel):
    timestamp: datetime = Field(default_factory=get_datetime_utc)
    from_agent: str
    to_agent: str
    reason: str = ""


class AgentStep(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    agent_id: uuid.UUID | None = None
    agent_name: str
    role: str
    input: str = ""
    output: str = ""
    thinking: str | None = None
    title_candidates: list[str] = Field(default_factory=list)
    status: str = "pending"  # pending | running | done | failed
    started_at: datetime | None = None
    ended_at: datetime | None = None
    # Agentic loop fields (all with defaults for backward compat)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    skills_activated: list[str] = Field(default_factory=list)
    iteration_count: int = 0


class WorkflowInput(BaseModel):
    topic: str  # 必填：写什么主题
    style_hints: list[str] = Field(default_factory=list)  # 可选：风格偏好提示
    article_ids: list[uuid.UUID] = Field(default_factory=list)  # 可选：手动指定参考文章
    auto_match_styles: bool = True  # 是否启用自动风格匹配
    content: str | None = None  # 保留向后兼容


class WorkflowRun(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: str = "writing"
    input: WorkflowInput = Field(default_factory=WorkflowInput)
    status: str = "pending"  # pending | running | waiting_human | done | failed | interrupted
    error_message: str | None = None  # Error message when status is failed
    steps: list[AgentStep] = Field(default_factory=list)
    parent_run_id: uuid.UUID | None = None
    user_feedback: str | None = None
    celery_task_id: str | None = None
    final_output: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime = Field(default_factory=get_datetime_utc)
    # Orchestrator fields (all with defaults for backward compat)
    use_orchestrator: bool = False
    orchestrator_messages: list[dict[str, Any]] = Field(default_factory=list)
    routing_log: list[RoutingEvent] = Field(default_factory=list)
    iteration_count: int = 0

    class Settings:
        name = "workflow_runs"


class WorkflowRunCreate(BaseModel):
    type: str = "writing"
    topic: str  # 必填：写什么主题
    style_hints: list[str] = Field(default_factory=list)  # 可选：风格偏好提示
    article_ids: list[uuid.UUID] = Field(default_factory=list)  # 可选：手动指定参考文章
    auto_match_styles: bool = True  # 是否启用自动风格匹配
    use_orchestrator: bool = False


class WorkflowRunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    input: WorkflowInput
    status: str
    error_message: str | None
    steps: list[AgentStep]
    parent_run_id: uuid.UUID | None
    user_feedback: str | None
    final_output: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    use_orchestrator: bool
    routing_log: list[RoutingEvent]
    iteration_count: int


class WorkflowRunsPublic(BaseModel):
    data: list[WorkflowRunPublic]
    count: int


class WorkflowApprove(BaseModel):
    selected_title: str


class WorkflowReject(BaseModel):
    feedback: str
