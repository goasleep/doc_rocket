"""TaskRun model — unified execution log for all Celery tasks."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel


class TaskRun(Document):
    class Settings:
        name = "task_runs"
        indexes = [
            IndexModel([("entity_id", 1)]),
            IndexModel([("task_type", 1), ("status", 1)]),
            IndexModel([("created_at", -1)]),
            IndexModel([("workflow_run_id", 1)]),
        ]

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_type: Literal["analyze", "fetch", "refine", "workflow"]
    celery_task_id: str | None = None

    # Trigger source
    triggered_by: Literal["manual", "scheduler", "agent"] = "manual"
    triggered_by_label: str | None = None  # Agent name, only when triggered_by="agent"

    # Associated entity (article or source)
    entity_type: Literal["article", "source"] | None = None
    entity_id: uuid.UUID | None = None
    entity_name: str | None = None  # Denormalized to avoid JOIN on query

    # Lifecycle
    status: Literal["pending", "running", "done", "failed"] = "pending"
    error_message: str | None = None

    # Writing workflow link
    workflow_run_id: uuid.UUID | None = None

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    ended_at: datetime | None = None


class TaskRunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_type: Literal["analyze", "fetch", "refine", "workflow"]
    celery_task_id: str | None
    triggered_by: Literal["manual", "scheduler", "agent"]
    triggered_by_label: str | None
    entity_type: Literal["article", "source"] | None
    entity_id: uuid.UUID | None
    entity_name: str | None
    status: Literal["pending", "running", "done", "failed"]
    error_message: str | None
    workflow_run_id: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class TaskRunsPublic(BaseModel):
    data: list[TaskRunPublic]
    count: int
