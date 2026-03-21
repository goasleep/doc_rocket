"""Tests for the writing workflow Celery task (calls _writing_workflow_async directly)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.fixtures.content import (  # noqa: F401
    sample_source,
    analyzed_article,
    sample_agent_configs,
    sample_workflow_run,
    fake_redis_sync,
)
from tests.fixtures.llm import (  # noqa: F401
    MOCK_EDITOR_RESPONSE,
)


@pytest.mark.anyio
async def test_workflow_runs_all_agents_and_pauses(
    db: None,
    sample_workflow_run,
    sample_agent_configs,
    fake_redis_sync,
):
    """Full pipeline: Writer→Editor→Reviewer, ends in waiting_human, publishes events."""
    from app.tasks.workflow import _writing_workflow_async
    from app.models import WorkflowRun

    published_events = []

    original_publish = fake_redis_sync.publish

    def capture_publish(channel, message):
        published_events.append(json.loads(message))
        return original_publish(channel, message)

    fake_redis_sync.publish = capture_publish

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(side_effect=[
        "这是Writer的初稿内容。",         # writer
        MOCK_EDITOR_RESPONSE.content,    # editor (JSON string)
        json.dumps({                     # reviewer
            "fact_check_flags": [],
            "legal_notes": [],
            "format_issues": [],
        }),
    ])

    with patch("app.core.agents.base.create_agent_for_config", return_value=mock_agent):
        await _writing_workflow_async(str(sample_workflow_run.id))

    run = await WorkflowRun.find_one(WorkflowRun.id == sample_workflow_run.id)
    assert run is not None
    assert run.status == "waiting_human"
    assert len(run.steps) == 3

    event_types = [e["type"] for e in published_events]
    assert event_types.count("agent_start") == 3
    assert event_types.count("agent_output") == 3
    assert "workflow_paused" in event_types


@pytest.mark.anyio
async def test_workflow_editor_step_stores_title_candidates(
    db: None,
    sample_workflow_run,
    sample_agent_configs,
    fake_redis_sync,
):
    """Editor step should extract title_candidates from JSON response."""
    from app.tasks.workflow import _writing_workflow_async
    from app.models import WorkflowRun

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(side_effect=[
        "初稿内容",
        MOCK_EDITOR_RESPONSE.content,
        json.dumps({"fact_check_flags": [], "legal_notes": [], "format_issues": []}),
    ])

    with patch("app.core.agents.base.create_agent_for_config", return_value=mock_agent):
        await _writing_workflow_async(str(sample_workflow_run.id))

    run = await WorkflowRun.find_one(WorkflowRun.id == sample_workflow_run.id)
    assert run is not None
    editor_step = next(s for s in run.steps if s.role == "editor")
    assert editor_step.title_candidates is not None
    assert len(editor_step.title_candidates) == 3


@pytest.mark.anyio
async def test_workflow_idempotent_skips_running_run(
    db: None,
    sample_workflow_run,
    sample_agent_configs,
    fake_redis_sync,
):
    """If status is already 'running', the workflow should not execute again."""
    from app.tasks.workflow import _writing_workflow_async
    from app.models import WorkflowRun

    sample_workflow_run.status = "running"
    await sample_workflow_run.save()

    with patch("app.core.agents.base.create_agent_for_config") as mock_create:
        await _writing_workflow_async(str(sample_workflow_run.id))

    mock_create.assert_not_called()
    run = await WorkflowRun.find_one(WorkflowRun.id == sample_workflow_run.id)
    assert run is not None
    assert run.status == "running"  # unchanged


@pytest.mark.anyio
async def test_workflow_agent_error_sets_failed(
    db: None,
    sample_workflow_run,
    sample_agent_configs,
    fake_redis_sync,
):
    """If an agent raises an exception, the run status should become 'failed'."""
    from app.tasks.workflow import _writing_workflow_async
    from app.models import WorkflowRun

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(side_effect=RuntimeError("LLM API error"))

    with (
        patch("app.core.agents.base.create_agent_for_config", return_value=mock_agent),
        pytest.raises(RuntimeError, match="LLM API error"),
    ):
        await _writing_workflow_async(str(sample_workflow_run.id))

    run = await WorkflowRun.find_one(WorkflowRun.id == sample_workflow_run.id)
    assert run is not None
    assert run.status == "failed"
