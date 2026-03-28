"""Background task manager for agent loop integration.

Tracks background Celery tasks and provides notification handling
within the agent execution loop.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from celery.result import AsyncResult

from app.celery_app import celery_app


@dataclass
class BackgroundTask:
    """Represents a background task."""

    id: str
    command: str
    status: str  # pending | running | completed | failed
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class BackgroundTaskManager:
    """Manages background tasks within an agent loop.

    Tracks Celery tasks and provides notification integration
    with the agent's message loop.
    """

    # Maximum concurrent tasks per agent
    MAX_CONCURRENT_TASKS = 5

    def __init__(self):
        self.tasks: dict[str, BackgroundTask] = {}
        self._notification_queue: asyncio.Queue[BackgroundTask] = asyncio.Queue()

    async def submit(
        self,
        task_id: str,
        command: str,
    ) -> str:
        """Register a submitted background task.

        Args:
            task_id: The Celery task ID
            command: The command being executed

        Returns:
            The task ID
        """
        # Check concurrent task limit
        running_count = sum(
            1 for t in self.tasks.values()
            if t.status in ("pending", "running")
        )
        if running_count >= self.MAX_CONCURRENT_TASKS:
            raise RuntimeError(
                f"Maximum concurrent tasks ({self.MAX_CONCURRENT_TASKS}) reached. "
                "Wait for some tasks to complete before submitting more."
            )

        task = BackgroundTask(
            id=task_id,
            command=command,
            status="pending",
        )
        self.tasks[task_id] = task

        # Start polling for this task
        asyncio.create_task(self._poll_task(task_id))

        return task_id

    async def _poll_task(self, task_id: str) -> None:
        """Poll a Celery task for completion.

        Args:
            task_id: The task ID to poll
        """
        task = self.tasks.get(task_id)
        if not task:
            return

        task.status = "running"

        # Poll Celery result
        result = AsyncResult(task_id, app=celery_app)

        # Wait for completion with polling
        while not result.ready():
            await asyncio.sleep(2)  # Poll every 2 seconds

        # Task is complete
        task.completed_at = datetime.now(timezone.utc)

        if result.successful():
            task.status = "completed"
            task.result = result.get()
        else:
            task.status = "failed"
            task.error = str(result.get(propagate=False))

        # Add to notification queue
        await self._notification_queue.put(task)

    def drain_notifications(self) -> list[BackgroundTask]:
        """Get all completed task notifications.

        Returns:
            List of completed/failed tasks since last check
        """
        notifications: list[BackgroundTask] = []

        while not self._notification_queue.empty():
            try:
                task = self._notification_queue.get_nowait()
                notifications.append(task)
            except asyncio.QueueEmpty:
                break

        return notifications

    def check(self, task_id: str) -> BackgroundTask | None:
        """Check the status of a specific task.

        Args:
            task_id: The task ID to check

        Returns:
            BackgroundTask if found, None otherwise
        """
        return self.tasks.get(task_id)

    def list_active(self) -> list[BackgroundTask]:
        """List all active (pending or running) tasks.

        Returns:
            List of active tasks
        """
        return [
            t for t in self.tasks.values()
            if t.status in ("pending", "running")
        ]

    def format_notifications(self, notifications: list[BackgroundTask]) -> str:
        """Format task notifications for agent consumption.

        Args:
            notifications: List of completed tasks

        Returns:
            Formatted notification message
        """
        if not notifications:
            return ""

        parts = ["[Background Task Notifications]"]

        for task in notifications:
            if task.status == "completed":
                result = task.result or {}
                parts.append(
                    f"\n✓ Task {task.id[:8]}... completed\n"
                    f"  Command: {task.command[:50]}...\n"
                    f"  Exit code: {result.get('exit_code', 'N/A')}\n"
                    f"  Output: {result.get('stdout', '')[:200]}"
                )
            else:
                parts.append(
                    f"\n✗ Task {task.id[:8]}... failed\n"
                    f"  Command: {task.command[:50]}...\n"
                    f"  Error: {task.error or 'Unknown error'}"
                )

        return "\n".join(parts)

    def get_status_summary(self) -> dict[str, Any]:
        """Get a summary of all tracked tasks.

        Returns:
            Dict with task counts and status
        """
        counts: dict[str, int] = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
        }

        for task in self.tasks.values():
            counts[task.status] = counts.get(task.status, 0) + 1

        return {
            "total": len(self.tasks),
            "active": counts["pending"] + counts["running"],
            "completed": counts["completed"],
            "failed": counts["failed"],
            "counts": counts,
        }
