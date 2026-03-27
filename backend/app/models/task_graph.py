"""Task graph model for DAG-based task dependency management."""
import uuid
from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class TaskNode(Document):
    """A node in the task graph representing a single task.

    Tasks form a DAG through blocked_by/blocks relationships.
    When a task completes, tasks blocked by it become ready.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workflow_run_id: uuid.UUID
    subject: str  # Task title/subject
    description: str = ""  # Detailed description
    status: str = "pending"  # pending | in_progress | completed | failed
    owner: str | None = None  # Agent or process that claimed the task

    # Dependency tracking (DAG edges)
    blocked_by: list[uuid.UUID] = Field(default_factory=list)  # Task IDs this task depends on
    blocks: list[uuid.UUID] = Field(default_factory=list)  # Task IDs that depend on this task

    # Timestamps
    created_at: datetime = Field(default_factory=get_datetime_utc)
    claimed_at: datetime | None = None
    completed_at: datetime | None = None

    # Optional metadata
    priority: int = 0  # Higher = more important
    task_type: str = "general"  # Task categorization
    result: str | None = None  # Task result/output
    error_message: str | None = None  # Error if failed

    class Settings:
        name = "task_nodes"
        indexes = [
            "workflow_run_id",
            "status",
            "owner",
            [("workflow_run_id", 1), ("status", 1)],
        ]

    @property
    def is_ready(self) -> bool:
        """Check if task is ready to be claimed (all dependencies completed)."""
        if self.status != "pending":
            return False
        # Task is ready if no pending dependencies
        # Note: This requires checking the database for actual dependency statuses
        return True

    def mark_claimed(self, owner: str) -> None:
        """Mark task as claimed by an owner."""
        self.status = "in_progress"
        self.owner = owner
        self.claimed_at = get_datetime_utc()

    def mark_completed(self, result: str | None = None) -> None:
        """Mark task as completed."""
        self.status = "completed"
        self.result = result
        self.completed_at = get_datetime_utc()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed."""
        self.status = "failed"
        self.error_message = error
        self.completed_at = get_datetime_utc()
