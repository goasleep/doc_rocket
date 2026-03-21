import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


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


class WorkflowInput(BaseModel):
    article_ids: list[uuid.UUID] = Field(default_factory=list)
    topic: str | None = None
    content: str | None = None


class WorkflowRun(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: str = "writing"
    input: WorkflowInput = Field(default_factory=WorkflowInput)
    status: str = "pending"  # pending | running | waiting_human | done | failed
    steps: list[AgentStep] = Field(default_factory=list)
    parent_run_id: uuid.UUID | None = None
    user_feedback: str | None = None
    celery_task_id: str | None = None
    final_output: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime = Field(default_factory=get_datetime_utc)

    class Settings:
        name = "workflow_runs"


class WorkflowRunCreate(BaseModel):
    type: str = "writing"
    article_ids: list[uuid.UUID] = Field(default_factory=list)
    topic: str | None = None


class WorkflowRunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    input: WorkflowInput
    status: str
    steps: list[AgentStep]
    parent_run_id: uuid.UUID | None
    user_feedback: str | None
    final_output: str | None
    created_by: uuid.UUID | None
    created_at: datetime


class WorkflowRunsPublic(BaseModel):
    data: list[WorkflowRunPublic]
    count: int


class WorkflowApprove(BaseModel):
    selected_title: str


class WorkflowReject(BaseModel):
    feedback: str
