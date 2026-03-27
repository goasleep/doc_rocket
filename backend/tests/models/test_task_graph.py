"""Tests for TaskNode model and TaskGraphManager."""
import uuid
import pytest
from datetime import datetime, timezone


class TestTaskNode:
    """Test cases for TaskNode document model."""

    @pytest.mark.anyio
    async def test_create_task_node(self, db: None):
        """Test creating a basic task node."""
        from app.models.task_graph import TaskNode

        workflow_id = uuid.uuid4()
        task = TaskNode(
            workflow_run_id=workflow_id,
            subject="Test Task",
            description="A test task",
            priority=5,
        )

        assert task.subject == "Test Task"
        assert task.description == "A test task"
        assert task.status == "pending"
        assert task.priority == 5
        assert task.workflow_run_id == workflow_id
        assert task.blocked_by == []
        assert task.blocks == []

    @pytest.mark.anyio
    async def test_mark_claimed(self, db: None):
        """Test marking a task as claimed."""
        from app.models.task_graph import TaskNode

        task = TaskNode(
            workflow_run_id=uuid.uuid4(),
            subject="Test Task",
        )

        task.mark_claimed("writer-agent")

        assert task.status == "in_progress"
        assert task.owner == "writer-agent"
        assert task.claimed_at is not None

    @pytest.mark.anyio
    async def test_mark_completed(self, db: None):
        """Test marking a task as completed."""
        from app.models.task_graph import TaskNode

        task = TaskNode(
            workflow_run_id=uuid.uuid4(),
            subject="Test Task",
        )

        task.mark_completed(result="Task completed successfully")

        assert task.status == "completed"
        assert task.result == "Task completed successfully"
        assert task.completed_at is not None

    @pytest.mark.anyio
    async def test_mark_failed(self, db: None):
        """Test marking a task as failed."""
        from app.models.task_graph import TaskNode

        task = TaskNode(
            workflow_run_id=uuid.uuid4(),
            subject="Test Task",
        )

        task.mark_failed("Something went wrong")

        assert task.status == "failed"
        assert task.error_message == "Something went wrong"
        assert task.completed_at is not None


class TestTaskGraphManager:
    """Test cases for TaskGraphManager."""

    @pytest.mark.anyio
    async def test_create_task(self, db: None):
        """Test creating a task."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        task = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Write draft",
            description="Create initial draft",
            priority=5,
        )

        assert task.subject == "Write draft"
        assert task.status == "pending"
        assert task.priority == 5

    @pytest.mark.anyio
    async def test_create_task_with_dependencies(self, db: None):
        """Test creating a task with dependencies."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        # Create first task
        task1 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Research",
        )

        # Create second task that depends on first
        task2 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Write",
            blocked_by=[task1.id],
        )

        assert task2.blocked_by == [task1.id]

        # Refresh task1 from DB to get updated blocks
        from app.models.task_graph import TaskNode
        task1_refreshed = await TaskNode.find_one(TaskNode.id == task1.id)
        assert task1_refreshed.blocks == [task2.id]

    @pytest.mark.anyio
    async def test_claim_task(self, db: None):
        """Test claiming a ready task."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        task = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Ready task",
        )

        claimed = await manager.claim_task(task.id, "writer-agent")

        assert claimed is not None
        assert claimed.status == "in_progress"
        assert claimed.owner == "writer-agent"

    @pytest.mark.anyio
    async def test_claim_task_with_unfinished_dependencies(self, db: None):
        """Test that task with unfinished deps cannot be claimed."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        task1 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Dependency",
        )
        task2 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Dependent",
            blocked_by=[task1.id],
        )

        # Try to claim task2 before task1 is done
        claimed = await manager.claim_task(task2.id, "writer-agent")

        assert claimed is None

    @pytest.mark.anyio
    async def test_complete_task_unblocks_dependents(self, db: None):
        """Test that completing a task unblocks dependent tasks."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        task1 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="First",
        )
        task2 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Second",
            blocked_by=[task1.id],
        )

        # Complete first task
        completed, unblocked = await manager.complete_task(task1.id)

        assert completed.status == "completed"
        assert len(unblocked) == 1
        assert unblocked[0].id == task2.id

    @pytest.mark.anyio
    async def test_get_ready_tasks(self, db: None):
        """Test getting all ready tasks."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        # Create tasks
        task1 = await manager.create_task(workflow_run_id=workflow_id, subject="Ready 1")
        task2 = await manager.create_task(workflow_run_id=workflow_id, subject="Ready 2")
        task3 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Blocked",
            blocked_by=[task1.id],
        )

        ready = await manager.get_ready_tasks(workflow_id)
        ready_ids = {t.id for t in ready}

        assert task1.id in ready_ids
        assert task2.id in ready_ids
        assert task3.id not in ready_ids

    @pytest.mark.anyio
    async def test_get_ready_tasks_sorted_by_priority(self, db: None):
        """Test that ready tasks are sorted by priority."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        task1 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="Low priority",
            priority=1,
        )
        task2 = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="High priority",
            priority=10,
        )

        ready = await manager.get_ready_tasks(workflow_id)

        assert ready[0].id == task2.id  # Higher priority first
        assert ready[1].id == task1.id

    @pytest.mark.anyio
    async def test_detect_cycles_no_cycles(self, db: None):
        """Test cycle detection with no cycles."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        # Create linear chain: A -> B -> C
        task_a = await manager.create_task(workflow_run_id=workflow_id, subject="A")
        task_b = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="B",
            blocked_by=[task_a.id],
        )
        task_c = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="C",
            blocked_by=[task_b.id],
        )

        cycles = await manager.detect_cycles(workflow_id)

        assert len(cycles) == 0

    @pytest.mark.anyio
    async def test_detect_cycles_with_cycle(self, db: None):
        """Test cycle detection finds cycles."""
        from app.core.agents.task_graph import TaskGraphManager
        from app.models.task_graph import TaskNode

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        # Create cycle: A -> B -> C -> A
        task_a = await manager.create_task(workflow_run_id=workflow_id, subject="A")
        task_b = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="B",
            blocked_by=[task_a.id],
        )
        task_c = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="C",
            blocked_by=[task_b.id],
        )

        # Manually create the cycle (normally prevented by _would_create_cycle)
        # Reload tasks from DB to ensure we have fresh state
        task_a = await TaskNode.find_one(TaskNode.id == task_a.id)
        task_c = await TaskNode.find_one(TaskNode.id == task_c.id)

        # Now create the cycle: A depends on C (C -> A)
        task_a.blocked_by.append(task_c.id)
        await task_a.save()

        # Update reverse relationship: C blocks A
        task_c.blocks.append(task_a.id)
        await task_c.save()

        # Debug: refresh and check
        task_a_refreshed = await TaskNode.find_one(TaskNode.id == task_a.id)
        task_b_refreshed = await TaskNode.find_one(TaskNode.id == task_b.id)
        task_c_refreshed = await TaskNode.find_one(TaskNode.id == task_c.id)
        print(f"task_a.blocked_by: {task_a_refreshed.blocked_by}")
        print(f"task_a.blocks: {task_a_refreshed.blocks}")
        print(f"task_b.blocked_by: {task_b_refreshed.blocked_by}")
        print(f"task_b.blocks: {task_b_refreshed.blocks}")
        print(f"task_c.blocked_by: {task_c_refreshed.blocked_by}")
        print(f"task_c.blocks: {task_c_refreshed.blocks}")

        cycles = await manager.detect_cycles(workflow_id)
        print(f"cycles: {cycles}")

        assert len(cycles) > 0

    @pytest.mark.anyio
    async def test_would_create_cycle_detection(self, db: None):
        """Test that cycle prevention works."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        # Create chain: A -> B
        task_a = await manager.create_task(workflow_run_id=workflow_id, subject="A")
        task_b = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="B",
            blocked_by=[task_a.id],
        )

        # Try to make C depend on B, then make A depend on C (would create cycle)
        task_c = await manager.create_task(
            workflow_run_id=workflow_id,
            subject="C",
            blocked_by=[task_b.id],
        )

        # This should detect a cycle
        would_cycle = await manager._would_create_cycle(task_a.id, task_c.id)

        assert would_cycle is True

    @pytest.mark.anyio
    async def test_get_task_graph_status(self, db: None):
        """Test getting overall task graph status."""
        from app.core.agents.task_graph import TaskGraphManager

        manager = TaskGraphManager()
        workflow_id = uuid.uuid4()

        # Create tasks in various states
        task1 = await manager.create_task(workflow_run_id=workflow_id, subject="Pending 1")
        task2 = await manager.create_task(workflow_run_id=workflow_id, subject="Pending 2")
        task3 = await manager.create_task(workflow_run_id=workflow_id, subject="In Progress")

        # Claim one task
        await manager.claim_task(task3.id, "agent")

        status = await manager.get_task_graph_status(workflow_id)

        assert status["total_tasks"] == 3
        assert status["status_counts"]["pending"] == 2
        assert status["status_counts"]["in_progress"] == 1
        assert status["ready_tasks"] == 2
        assert status["has_cycles"] is False
        assert status["is_complete"] is False
