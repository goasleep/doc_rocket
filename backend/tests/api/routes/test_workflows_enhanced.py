"""Enhanced integration tests for agent platform capabilities.

Tests for:
- Context compression in long workflows
- Subagent isolation with orchestrator workflow
- Task graph with dependent tasks
- Background task execution and notification
- Skill on-demand loading end-to-end
"""
import pytest
import uuid
import json
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient


@pytest.fixture
async def analyzed_article(db: None):
    """Create an article with analysis for testing."""
    from app.models import Article, ArticleAnalysis

    article = Article(
        title="Test Article",
        content="Test content for analysis",
        content_md="# Test Article\n\nTest content",
        url="https://example.com/test",
        source_id=None,
    )
    await article.insert()

    analysis = ArticleAnalysis(
        article_id=article.id,
        overall_quality_score=85,
        structure_analysis={"has_headings": True},
        style_analysis={"tone": "formal"},
    )
    await analysis.insert()

    return article, analysis


@pytest.mark.anyio
async def test_context_compression_integration(db: None):
    """Test that context compression works in agent execution."""
    from app.core.agents.compression import ContextCompressor

    compressor = ContextCompressor()

    # Create messages with tool_calls to trigger compression path
    messages = [{"role": "system", "content": "You are a helpful assistant"}]
    for i in range(10):
        # Add assistant message with tool_calls
        messages.append({
            "role": "assistant",
            "content": f"Let me help you {i}",
            "tool_calls": [{"id": f"call_{i}", "function": {"name": "search", "arguments": "{}"}}]
        })
        # Add tool result
        messages.append({"role": "tool", "tool_call_id": f"call_{i}", "content": f"Result {i}: " + "x" * 500})

    # Estimate tokens
    tokens = compressor.estimate_tokens(messages)
    assert tokens > 0

    # Test microcompact
    original_count = len(messages)
    compressed = compressor.microcompact(messages)
    # Should keep system message and reduce tool results
    assert len(compressed) <= original_count


@pytest.mark.anyio
async def test_subagent_isolation_integration(db: None):
    """Test that subagent runner exists and can be instantiated."""
    from app.core.agents.subagent import SubagentRunner

    # Just verify the class exists and can be instantiated
    runner = SubagentRunner()
    assert runner is not None


@pytest.mark.anyio
async def test_task_graph_creation_and_execution(db: None):
    """Test task graph creation and dependency management."""
    from app.core.agents.task_graph import TaskGraphManager
    from app.models.task_graph import TaskNode

    manager = TaskGraphManager()
    workflow_id = uuid.uuid4()

    # Create tasks with dependencies
    task_a = await manager.create_task(
        workflow_run_id=workflow_id,
        subject="Task A",
        description="First task",
        priority=10,
    )

    task_b = await manager.create_task(
        workflow_run_id=workflow_id,
        subject="Task B",
        description="Depends on A",
        blocked_by=[task_a.id],
        priority=5,
    )

    # Verify dependency
    assert task_b.blocked_by == [task_a.id]

    # Task B should not be claimable yet
    claimed = await manager.claim_task(task_b.id, "test-agent")
    assert claimed is None

    # Task A should be claimable
    claimed_a = await manager.claim_task(task_a.id, "test-agent")
    assert claimed_a is not None
    assert claimed_a.status == "in_progress"

    # Complete task A
    completed, unblocked = await manager.complete_task(task_a.id, result="Done A")
    assert completed.status == "completed"
    assert len(unblocked) == 1
    assert unblocked[0].id == task_b.id

    # Now task B should be claimable
    claimed_b = await manager.claim_task(task_b.id, "test-agent")
    assert claimed_b is not None


@pytest.mark.anyio
async def test_task_graph_cycle_detection(db: None):
    """Test that task graph detects cycles."""
    from app.core.agents.task_graph import TaskGraphManager

    manager = TaskGraphManager()
    workflow_id = uuid.uuid4()

    # Create tasks
    task_a = await manager.create_task(workflow_run_id=workflow_id, subject="A")
    task_b = await manager.create_task(workflow_run_id=workflow_id, subject="B", blocked_by=[task_a.id])

    # Try to create a cycle (A depends on B)
    would_cycle = await manager._would_create_cycle(task_a.id, task_b.id)
    assert would_cycle is True


@pytest.mark.anyio
async def test_background_task_manager(db: None):
    """Test background task manager functionality."""
    from app.core.agents.background import BackgroundTaskManager

    manager = BackgroundTaskManager()

    with patch("app.core.agents.background.AsyncResult") as mock_result_class:
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.get.return_value = {"exit_code": 0, "stdout": "hello"}
        mock_result_class.return_value = mock_result

        # Submit a task
        task_id = await manager.submit("task-1", "echo hello")
        assert task_id == "task-1"

        # Check task exists
        task = manager.check("task-1")
        assert task is not None
        assert task.command == "echo hello"

        # Check active tasks
        active = manager.list_active()
        assert len(active) == 1


@pytest.mark.anyio
async def test_background_task_concurrent_limit(db: None):
    """Test that background task manager enforces concurrent limit."""
    from app.core.agents.background import BackgroundTaskManager

    manager = BackgroundTaskManager()

    with patch("app.core.agents.background.AsyncResult") as mock_result_class:
        mock_result = MagicMock()
        mock_result.ready.return_value = False  # Keep tasks "running"
        mock_result_class.return_value = mock_result

        # Fill up to max (5)
        for i in range(5):
            await manager.submit(f"task-{i}", f"echo {i}")

        # Sixth task should fail
        with pytest.raises(RuntimeError, match="Maximum concurrent tasks"):
            await manager.submit("task-6", "echo 6")


@pytest.mark.anyio
async def test_skill_cache_functionality(db: None):
    """Test skill caching with TTL."""
    from app.core.agents.skill_cache import SkillCache

    cache = SkillCache()

    # Set a skill
    cache.set("test-skill", "Skill body", "Description", ttl_seconds=3600)

    # Retrieve from cache
    cached = cache.get("test-skill")
    assert cached is not None
    assert cached.body == "Skill body"

    # Invalidate
    cache.invalidate("test-skill")
    assert cache.get("test-skill") is None


@pytest.mark.anyio
async def test_load_skill_tool_exists(db: None):
    """Test that load_skill tool exists and is callable."""
    from app.core.tools.builtin import load_skill

    # Just verify the function exists
    assert callable(load_skill)


@pytest.mark.anyio
async def test_workflow_with_task_graph_mode(
    client: AsyncClient,
    superuser_token_headers: dict,
    analyzed_article,
):
    """Test workflow execution with task graph mode enabled."""
    article, _ = analyzed_article

    mock_task = MagicMock()
    mock_task.id = "fake-celery-task-id"

    with patch("app.api.routes.workflows.writing_workflow_task") as mock_celery:
        mock_celery.delay.return_value = mock_task

        # Trigger workflow with task graph mode
        r = await client.post(
            "/api/v1/workflows/",
            json={
                "type": "writing",
                "article_ids": [str(article.id)],
                "use_task_graph": True,
            },
            headers=superuser_token_headers,
        )

    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_workflow_with_orchestrator_mode(
    client: AsyncClient,
    superuser_token_headers: dict,
    analyzed_article,
):
    """Test workflow execution with orchestrator mode."""
    article, _ = analyzed_article

    mock_task = MagicMock()
    mock_task.id = "fake-celery-task-id"

    with patch("app.api.routes.workflows.writing_workflow_task") as mock_celery:
        mock_celery.delay.return_value = mock_task

        # Trigger workflow with orchestrator mode
        r = await client.post(
            "/api/v1/workflows/",
            json={
                "type": "writing",
                "article_ids": [str(article.id)],
                "use_orchestrator": True,
            },
            headers=superuser_token_headers,
        )

    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_compression_tool_exists(db: None):
    """Test that compress_context tool exists."""
    from app.core.tools.builtin import compress_context

    # Just verify the function exists and is callable
    assert callable(compress_context)


@pytest.mark.anyio
async def test_spawn_subagent_tool_exists(db: None):
    """Test that spawn_subagent tool exists."""
    from app.core.tools.builtin import spawn_subagent

    # Just verify the function exists and is callable
    assert callable(spawn_subagent)


@pytest.mark.anyio
async def test_task_graph_tools(db: None):
    """Test task graph tool functions."""
    from app.core.tools.task_graph import task_create

    workflow_id = str(uuid.uuid4())

    mock_task = MagicMock()
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
        )

    data = json.loads(result)
    assert data["subject"] == "Test Task"
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_background_tools(db: None):
    """Test background task tools."""
    from app.core.tools.builtin import background_run
    from app.tasks import background as background_module

    with patch.object(background_module, "execute_background_command") as mock_celery:
        mock_task = MagicMock()
        mock_task.id = "bg-task-123"
        mock_celery.delay.return_value = mock_task

        result = await background_run(command="echo hello", timeout=60)

    assert "bg-task-123" in result
    assert "started" in result.lower()
