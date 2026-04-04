"""Regression tests for the linear pipeline (use_orchestrator=False).

These tests verify that when ``use_orchestrator`` is ``False`` the workflow
calls the agents in Writer→Editor→Reviewer order, publishes the expected SSE
event types, and leaves the ``WorkflowRun`` in status ``"waiting_human"``.
"""
import json
from unittest.mock import AsyncMock, patch, call

import pytest

from tests.fixtures.content import (  # noqa: F401
    sample_source,
    analyzed_article,
    sample_agent_configs,
    sample_workflow_run,
    fake_redis_sync,
)
from tests.fixtures.llm import MOCK_EDITOR_RESPONSE  # noqa: F401


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_agent(*side_effects):
    """Return an AsyncMock agent whose ``run`` returns side_effects in order."""
    agent = AsyncMock()
    agent.run = AsyncMock(side_effect=list(side_effects))
    return agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_linear_pipeline_calls_agents_in_order(
    db: None,
    sample_workflow_run,
    sample_agent_configs,
    fake_redis_sync,
):
    """Writer, Editor, and Reviewer agents are invoked in workflow_order sequence."""
    from app.tasks.workflow import _writing_workflow_async
    from app.models import WorkflowRun

    # Ensure the run uses the linear path
    sample_workflow_run.use_orchestrator = False
    await sample_workflow_run.save()

    call_order: list[str] = []

    async def _side_effect_writer(prompt: str) -> str:
        call_order.append("writer")
        return "Writer draft content."

    async def _side_effect_editor(content: str) -> str:
        call_order.append("editor")
        return MOCK_EDITOR_RESPONSE.content

    async def _side_effect_reviewer(content: str) -> str:
        call_order.append("reviewer")
        return json.dumps({"fact_check_flags": [], "legal_notes": [], "format_issues": []})

    side_effects = [
        _side_effect_writer,
        _side_effect_editor,
        _side_effect_reviewer,
    ]
    index = 0

    # Each call to create_agent_for_config returns a fresh AsyncMock whose
    # run delegates to the next side-effect in the list.
    def _create_agent(config):
        nonlocal index
        agent = AsyncMock()
        agent.run = AsyncMock(side_effect=side_effects[index])
        index += 1
        return agent

    with patch("app.core.agents.base.create_agent_for_config", side_effect=_create_agent):
        await _writing_workflow_async(str(sample_workflow_run.id))

    assert call_order == ["writer", "editor", "reviewer"], (
        f"Agents were not called in expected order: {call_order}"
    )


@pytest.mark.anyio
async def test_linear_pipeline_publishes_sse_events(
    db: None,
    sample_workflow_run,
    sample_agent_configs,
    fake_redis_sync,
):
    """The workflow publishes agent_start, agent_output, and workflow_paused SSE events."""
    from app.tasks.workflow import _writing_workflow_async

    sample_workflow_run.use_orchestrator = False
    await sample_workflow_run.save()

    published_events: list[dict] = []
    original_publish = fake_redis_sync.publish

    def _capture(channel: str, message: str) -> None:
        published_events.append(json.loads(message))
        return original_publish(channel, message)

    fake_redis_sync.publish = _capture

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(
        side_effect=[
            "Writer draft content.",
            MOCK_EDITOR_RESPONSE.content,
            json.dumps({"fact_check_flags": [], "legal_notes": [], "format_issues": []}),
        ]
    )
    mock_humanizer = AsyncMock()
    mock_humanizer.run = AsyncMock(return_value="Humanized content.")

    with patch("app.core.agents.base.create_agent_for_config", return_value=mock_agent):
        with patch("app.tasks.workflow.BaseAgent", return_value=mock_humanizer):
            await _writing_workflow_async(str(sample_workflow_run.id))

    event_types = [e["type"] for e in published_events]

    # Three agents + humanizer → four agent_start events
    assert event_types.count("agent_start") == 4, (
        f"Expected 4 agent_start events, found {event_types.count('agent_start')}"
    )
    # Three agents + humanizer → four agent_output events
    assert event_types.count("agent_output") == 4, (
        f"Expected 4 agent_output events, found {event_types.count('agent_output')}"
    )
    # Pipeline ends → one workflow_paused event
    assert "workflow_paused" in event_types, (
        "workflow_paused event was never published"
    )


@pytest.mark.anyio
async def test_linear_pipeline_status_is_waiting_human(
    db: None,
    sample_workflow_run,
    sample_agent_configs,
    fake_redis_sync,
):
    """After a successful linear run the WorkflowRun status must be 'waiting_human'."""
    from app.tasks.workflow import _writing_workflow_async
    from app.models import WorkflowRun

    sample_workflow_run.use_orchestrator = False
    await sample_workflow_run.save()

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(
        side_effect=[
            "Writer draft content.",
            MOCK_EDITOR_RESPONSE.content,
            json.dumps({"fact_check_flags": [], "legal_notes": [], "format_issues": []}),
        ]
    )
    mock_humanizer = AsyncMock()
    mock_humanizer.run = AsyncMock(return_value="Humanized content.")

    with patch("app.core.agents.base.create_agent_for_config", return_value=mock_agent):
        with patch("app.tasks.workflow.BaseAgent", return_value=mock_humanizer):
            await _writing_workflow_async(str(sample_workflow_run.id))

    run = await WorkflowRun.find_one(WorkflowRun.id == sample_workflow_run.id)
    assert run is not None
    assert run.status == "waiting_human", (
        f"Expected status 'waiting_human', got '{run.status}'"
    )
    assert len(run.steps) == 4, (
        f"Expected 4 completed steps (writer, editor, reviewer, humanizer), found {len(run.steps)}"
    )
    step_statuses = [(s.agent_name, s.status) for s in run.steps]
    assert all(s.status == "done" for s in run.steps), (
        f"Not all agent steps have status 'done'. Steps: {step_statuses}"
    )
