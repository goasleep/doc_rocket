"""Tests for task graph tools."""
import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.core.tools.task_graph import (
    task_create,
    task_update,
    task_claim,
    task_complete,
    task_fail,
    task_list,
    task_get_ready,
    task_graph_status,
)


class TestTaskCreate:
    """Test cases for task_create tool."""

    @pytest.mark.anyio
    async def test_create_basic_task(self):
        """Test creating a basic task."""
        workflow_id = str(uuid.uuid4())

        mock_task = AsyncMock()
        mock_task.id = uuid.uuid4()
        mock_task.workflow_run_id = uuid.UUID(workflow_id)
        mock_task.subject = "Test Task"
        mock_task.description = "Description"
        mock_task.status = "pending"
        mock_task.blocked_by = []
        mock_task.priority = 5
        mock_task.task_type = "general"
        mock_task.created_at = None

        with patch("app.core.tools.task_graph.TaskGraphManager.create_task", return_value=mock_task):
            result = await task_create(
                workflow_run_id=workflow_id,
                subject="Test Task",
                description="Description",
                priority=5,
            )

        data = json.loads(result)
        assert data["subject"] == "Test Task"
        assert data["status"] == "pending"
        assert data["priority"] == 5

    @pytest.mark.anyio
    async def test_create_task_with_dependencies(self):
        """Test creating a task with dependencies."""
        workflow_id = str(uuid.uuid4())
        dep_id = str(uuid.uuid4())

        mock_task = AsyncMock()
        mock_task.id = uuid.uuid4()
        mock_task.workflow_run_id = uuid.UUID(workflow_id)
        mock_task.subject = "Dependent Task"
        mock_task.description = ""
        mock_task.status = "pending"
        mock_task.blocked_by = [uuid.UUID(dep_id)]
        mock_task.priority = 0
        mock_task.task_type = "general"
        mock_task.created_at = None

        with patch("app.core.tools.task_graph.TaskGraphManager.create_task", return_value=mock_task):
            result = await task_create(
                workflow_run_id=workflow_id,
                subject="Dependent Task",
                blocked_by=[dep_id],
            )

        data = json.loads(result)
        assert dep_id in data["blocked_by"]

    @pytest.mark.anyio
    async def test_create_task_invalid_workflow_id(self):
        """Test error handling for invalid workflow ID."""
        result = await task_create(
            workflow_run_id="invalid-uuid",
            subject="Test",
        )

        data = json.loads(result)
        assert "error" in data


class TestTaskClaim:
    """Test cases for task_claim tool."""

    @pytest.mark.anyio
    async def test_claim_ready_task(self):
        """Test claiming a ready task."""
        task_id = str(uuid.uuid4())

        mock_task = AsyncMock()
        mock_task.id = uuid.UUID(task_id)
        mock_task.subject = "Ready Task"
        mock_task.status = "in_progress"
        mock_task.owner = "writer-agent"
        mock_task.claimed_at = None

        with patch("app.core.tools.task_graph.TaskGraphManager.claim_task", return_value=mock_task):
            result = await task_claim(task_id=task_id, owner="writer-agent")

        data = json.loads(result)
        assert data["status"] == "in_progress"
        assert data["owner"] == "writer-agent"

    @pytest.mark.anyio
    async def test_claim_unavailable_task(self):
        """Test claiming a task that's not claimable."""
        task_id = str(uuid.uuid4())

        with patch("app.core.tools.task_graph.TaskGraphManager.claim_task", return_value=None):
            result = await task_claim(task_id=task_id, owner="writer-agent")

        data = json.loads(result)
        assert "error" in data


class TestTaskComplete:
    """Test cases for task_complete tool."""

    @pytest.mark.anyio
    async def test_complete_task(self):
        """Test completing a task."""
        task_id = str(uuid.uuid4())

        mock_task = AsyncMock()
        mock_task.id = uuid.UUID(task_id)
        mock_task.subject = "Completed Task"
        mock_task.status = "completed"
        mock_task.completed_at = None

        mock_unblocked = [AsyncMock()]
        mock_unblocked[0].id = uuid.uuid4()
        mock_unblocked[0].subject = "Unblocked Task"

        with patch("app.core.tools.task_graph.TaskGraphManager.complete_task", return_value=(mock_task, mock_unblocked)):
            result = await task_complete(task_id=task_id, result="Done!")

        data = json.loads(result)
        assert data["status"] == "completed"
        assert data["newly_unblocked_count"] == 1


class TestTaskList:
    """Test cases for task_list tool."""

    @pytest.mark.anyio
    async def test_list_tasks(self):
        """Test listing tasks."""
        workflow_id = str(uuid.uuid4())

        mock_tasks = [
            AsyncMock(),
            AsyncMock(),
        ]
        mock_tasks[0].id = uuid.uuid4()
        mock_tasks[0].subject = "Task 1"
        mock_tasks[0].status = "pending"
        mock_tasks[0].owner = None
        mock_tasks[0].priority = 1
        mock_tasks[0].blocked_by = []
        mock_tasks[0].created_at = None

        mock_tasks[1].id = uuid.uuid4()
        mock_tasks[1].subject = "Task 2"
        mock_tasks[1].status = "completed"
        mock_tasks[1].owner = "agent"
        mock_tasks[1].priority = 2
        mock_tasks[1].blocked_by = []
        mock_tasks[1].created_at = None

        with patch("app.core.tools.task_graph.TaskGraphManager.get_tasks_by_status", return_value=mock_tasks):
            result = await task_list(workflow_run_id=workflow_id)

        data = json.loads(result)
        assert data["count"] == 2
        assert len(data["tasks"]) == 2

    @pytest.mark.anyio
    async def test_list_tasks_with_status_filter(self):
        """Test listing tasks with status filter."""
        workflow_id = str(uuid.uuid4())

        mock_tasks = [AsyncMock()]
        mock_tasks[0].id = uuid.uuid4()
        mock_tasks[0].subject = "Task 1"
        mock_tasks[0].status = "pending"
        mock_tasks[0].owner = None
        mock_tasks[0].priority = 1
        mock_tasks[0].blocked_by = []
        mock_tasks[0].created_at = None

        with patch("app.core.tools.task_graph.TaskGraphManager.get_tasks_by_status", return_value=mock_tasks):
            result = await task_list(workflow_run_id=workflow_id, status="pending")

        data = json.loads(result)
        assert data["count"] == 1


class TestTaskGetReady:
    """Test cases for task_get_ready tool."""

    @pytest.mark.anyio
    async def test_get_ready_tasks(self):
        """Test getting ready tasks."""
        workflow_id = str(uuid.uuid4())

        mock_tasks = [
            AsyncMock(),
        ]
        mock_tasks[0].id = uuid.uuid4()
        mock_tasks[0].subject = "Ready Task"
        mock_tasks[0].description = "A ready task"
        mock_tasks[0].priority = 5
        mock_tasks[0].task_type = "general"

        with patch("app.core.tools.task_graph.TaskGraphManager.get_ready_tasks", return_value=mock_tasks):
            result = await task_get_ready(workflow_run_id=workflow_id)

        data = json.loads(result)
        assert data["count"] == 1
        assert data["tasks"][0]["subject"] == "Ready Task"


class TestTaskGraphStatus:
    """Test cases for task_graph_status tool."""

    @pytest.mark.anyio
    async def test_get_graph_status(self):
        """Test getting task graph status."""
        workflow_id = str(uuid.uuid4())

        mock_status = {
            "total_tasks": 5,
            "status_counts": {"pending": 2, "in_progress": 1, "completed": 2, "failed": 0},
            "ready_tasks": 2,
            "ready_task_ids": [],
            "has_cycles": False,
            "cycles": [],
            "is_complete": False,
        }

        with patch("app.core.tools.task_graph.TaskGraphManager.get_task_graph_status", return_value=mock_status):
            result = await task_graph_status(workflow_run_id=workflow_id)

        data = json.loads(result)
        assert data["total_tasks"] == 5
        assert data["status_counts"]["completed"] == 2
        assert data["has_cycles"] is False
