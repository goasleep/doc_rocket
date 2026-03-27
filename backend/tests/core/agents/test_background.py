"""Tests for BackgroundTaskManager."""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agents.background import BackgroundTask, BackgroundTaskManager


class TestBackgroundTask:
    """Test cases for BackgroundTask dataclass."""

    def test_task_creation(self):
        """Test creating a background task."""
        task = BackgroundTask(
            id="test-task-123",
            command="echo hello",
            status="pending",
        )

        assert task.id == "test-task-123"
        assert task.command == "echo hello"
        assert task.status == "pending"
        assert task.result is None
        assert task.created_at is not None


class TestBackgroundTaskManager:
    """Test cases for BackgroundTaskManager."""

    @pytest.mark.anyio
    async def test_submit_task(self):
        """Test submitting a background task."""
        manager = BackgroundTaskManager()

        with patch("app.core.agents.background.AsyncResult") as mock_result:
            mock_result.return_value.ready.return_value = True
            mock_result.return_value.successful.return_value = True
            mock_result.return_value.get.return_value = {"exit_code": 0, "stdout": "hello"}

            task_id = await manager.submit("task-123", "echo hello")

        assert task_id == "task-123"
        assert "task-123" in manager.tasks
        assert manager.tasks["task-123"].command == "echo hello"

    @pytest.mark.anyio
    async def test_submit_exceeds_max_concurrent(self):
        """Test that exceeding max concurrent tasks raises error."""
        manager = BackgroundTaskManager()

        # Fill up to max
        for i in range(5):
            with patch("app.core.agents.background.AsyncResult") as mock_result:
                mock_result.return_value.ready.return_value = False
                await manager.submit(f"task-{i}", f"echo {i}")

        # Sixth task should fail
        with pytest.raises(RuntimeError, match="Maximum concurrent tasks"):
            await manager.submit("task-6", "echo 6")

    @pytest.mark.anyio
    async def test_check_task(self):
        """Test checking a task status."""
        manager = BackgroundTaskManager()

        with patch("app.core.agents.background.AsyncResult") as mock_result:
            mock_result.return_value.ready.return_value = True
            mock_result.return_value.successful.return_value = True
            mock_result.return_value.get.return_value = {"exit_code": 0}

            await manager.submit("task-123", "echo hello")
            # Wait a bit for polling
            await asyncio.sleep(0.1)

        task = manager.check("task-123")
        assert task is not None
        assert task.command == "echo hello"

    @pytest.mark.anyio
    async def test_drain_notifications(self):
        """Test draining completed task notifications."""
        manager = BackgroundTaskManager()

        # Add a completed task to the queue
        completed_task = BackgroundTask(
            id="task-123",
            command="echo hello",
            status="completed",
            result={"exit_code": 0, "stdout": "hello"},
        )
        await manager._notification_queue.put(completed_task)

        notifications = manager.drain_notifications()

        assert len(notifications) == 1
        assert notifications[0].id == "task-123"
        assert notifications[0].status == "completed"

    @pytest.mark.anyio
    async def test_format_notifications(self):
        """Test formatting notifications for agent consumption."""
        manager = BackgroundTaskManager()

        notifications = [
            BackgroundTask(
                id="task-123",
                command="echo hello world this is a long command",
                status="completed",
                result={"exit_code": 0, "stdout": "hello output"},
            ),
            BackgroundTask(
                id="task-456",
                command="fail command",
                status="failed",
                error="Command failed",
            ),
        ]

        formatted = manager.format_notifications(notifications)

        assert "[Background Task Notifications]" in formatted
        assert "task-123" in formatted
        assert "task-456" in formatted
        assert "completed" in formatted
        assert "failed" in formatted

    @pytest.mark.anyio
    async def test_list_active(self):
        """Test listing active tasks."""
        manager = BackgroundTaskManager()

        # Add tasks in different states
        manager.tasks["pending-task"] = BackgroundTask(
            id="pending-task",
            command="echo 1",
            status="pending",
        )
        manager.tasks["running-task"] = BackgroundTask(
            id="running-task",
            command="echo 2",
            status="running",
        )
        manager.tasks["completed-task"] = BackgroundTask(
            id="completed-task",
            command="echo 3",
            status="completed",
        )

        active = manager.list_active()
        active_ids = {t.id for t in active}

        assert "pending-task" in active_ids
        assert "running-task" in active_ids
        assert "completed-task" not in active_ids

    def test_get_status_summary(self):
        """Test getting status summary."""
        manager = BackgroundTaskManager()

        manager.tasks["task-1"] = BackgroundTask(id="task-1", command="echo 1", status="pending")
        manager.tasks["task-2"] = BackgroundTask(id="task-2", command="echo 2", status="running")
        manager.tasks["task-3"] = BackgroundTask(id="task-3", command="echo 3", status="completed")
        manager.tasks["task-4"] = BackgroundTask(id="task-4", command="echo 4", status="completed")
        manager.tasks["task-5"] = BackgroundTask(id="task-5", command="echo 5", status="failed")

        summary = manager.get_status_summary()

        assert summary["total"] == 5
        assert summary["active"] == 2
        assert summary["completed"] == 2
        assert summary["counts"]["pending"] == 1
        assert summary["counts"]["running"] == 1
        assert summary["counts"]["completed"] == 2
        assert summary["counts"]["failed"] == 1
