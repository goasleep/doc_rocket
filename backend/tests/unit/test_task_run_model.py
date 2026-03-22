"""Unit tests for TaskRun model defaults and validation."""
import uuid

import pytest

from app.models.task_run import TaskRun


def test_task_run_defaults():
    """TaskRun should have correct default field values."""
    run = TaskRun(task_type="analyze")
    assert run.status == "pending"
    assert run.triggered_by == "manual"
    assert run.entity_id is None
    assert run.entity_type is None
    assert run.entity_name is None
    assert run.workflow_run_id is None
    assert run.celery_task_id is None
    assert run.error_message is None
    assert run.started_at is None
    assert run.ended_at is None
    assert run.triggered_by_label is None
    assert isinstance(run.id, uuid.UUID)


def test_task_run_entity_type_and_id_can_be_none():
    """topic-only workflow and initial fetch_url state allow entity_id=None."""
    run = TaskRun(task_type="workflow")
    assert run.entity_type is None
    assert run.entity_id is None


def test_task_run_entity_name_can_be_none():
    run = TaskRun(task_type="fetch")
    assert run.entity_name is None


def test_task_run_error_message_truncation():
    """Error messages exceeding 500 chars should be stored truncated in usage."""
    long_msg = "x" * 600
    truncated = long_msg[:500]
    assert len(truncated) == 500

    run = TaskRun(task_type="analyze", error_message=truncated)
    assert len(run.error_message) == 500  # type: ignore[arg-type]


def test_task_run_workflow_run_id_none():
    """Non-workflow tasks should allow workflow_run_id=None."""
    run = TaskRun(task_type="analyze")
    assert run.workflow_run_id is None


def test_task_run_with_article_entity():
    article_id = uuid.uuid4()
    run = TaskRun(
        task_type="analyze",
        entity_type="article",
        entity_id=article_id,
        entity_name="Test Article",
        triggered_by="manual",
    )
    assert run.entity_type == "article"
    assert run.entity_id == article_id
    assert run.entity_name == "Test Article"


def test_task_run_agent_trigger():
    run = TaskRun(
        task_type="analyze",
        triggered_by="agent",
        triggered_by_label="WriterAgent",
    )
    assert run.triggered_by == "agent"
    assert run.triggered_by_label == "WriterAgent"
