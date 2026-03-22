"""Tests for refine_article Celery task async logic."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from tests.fixtures.content import sample_article, sample_source  # noqa: F401
from tests.fixtures.llm import MOCK_ANALYSIS_RESPONSE


@pytest.mark.anyio
async def test_refine_success_writes_content_md(db: None, sample_article):
    """On success: content_md written, refine_status='refined', analyze enqueued."""
    from app.tasks.refine import _refine_article_async
    from app.models import Article, TaskRun

    task_run = TaskRun(
        task_type="refine",
        triggered_by="manual",
        entity_type="article",
        entity_id=sample_article.id,
        entity_name=sample_article.title,
        status="pending",
    )
    await task_run.insert()

    mock_analyze = MagicMock()
    mock_analyze.apply_async.return_value = MagicMock(id="celery-analyze-id")

    with (
        patch("app.core.agents.refiner.RefinerAgent.run", new=AsyncMock(return_value="# 精修后内容\n\n段落")),
        patch("app.tasks.analyze.analyze_article_task", mock_analyze),
    ):
        await _refine_article_async(str(sample_article.id), str(task_run.id))

    updated = await Article.find_one(Article.id == sample_article.id)
    assert updated is not None
    assert updated.content_md == "# 精修后内容\n\n段落"
    assert updated.refine_status == "refined"

    updated_run = await TaskRun.find_one(TaskRun.id == task_run.id)
    assert updated_run is not None
    assert updated_run.status == "done"

    # analyze_article_task should have been enqueued
    mock_analyze.apply_async.assert_called_once()


@pytest.mark.anyio
async def test_refine_failure_degrades_to_analyze(db: None, sample_article):
    """On failure: refine_status='failed', analyze still enqueued (degraded path)."""
    from app.tasks.refine import _refine_article_async
    from app.models import Article, TaskRun

    task_run = TaskRun(
        task_type="refine",
        triggered_by="scheduler",
        entity_type="article",
        entity_id=sample_article.id,
        entity_name=sample_article.title,
        status="pending",
    )
    await task_run.insert()

    mock_analyze = MagicMock()
    mock_analyze.apply_async.return_value = MagicMock(id="celery-analyze-id")

    with (
        patch("app.core.agents.refiner.RefinerAgent.run", new=AsyncMock(side_effect=RuntimeError("llm error"))),
        patch("app.tasks.analyze.analyze_article_task", mock_analyze),
    ):
        await _refine_article_async(str(sample_article.id), str(task_run.id))

    updated = await Article.find_one(Article.id == sample_article.id)
    assert updated is not None
    assert updated.refine_status == "failed"
    assert updated.content_md is None

    updated_run = await TaskRun.find_one(TaskRun.id == task_run.id)
    assert updated_run is not None
    assert updated_run.status == "failed"

    # analyze_article_task must still be enqueued despite failure
    mock_analyze.apply_async.assert_called_once()


@pytest.mark.anyio
async def test_refine_task_run_lifecycle(db: None, sample_article):
    """TaskRun transitions: pending → running → done."""
    from app.tasks.refine import _refine_article_async
    from app.models import TaskRun

    task_run = TaskRun(
        task_type="refine",
        triggered_by="manual",
        entity_type="article",
        entity_id=sample_article.id,
        entity_name=sample_article.title,
        status="pending",
    )
    await task_run.insert()

    mock_analyze = MagicMock()
    mock_analyze.apply_async.return_value = MagicMock(id="celery-analyze-id")

    with (
        patch("app.core.agents.refiner.RefinerAgent.run", new=AsyncMock(return_value="# content")),
        patch("app.tasks.analyze.analyze_article_task", mock_analyze),
    ):
        await _refine_article_async(str(sample_article.id), str(task_run.id))

    final_run = await TaskRun.find_one(TaskRun.id == task_run.id)
    assert final_run is not None
    assert final_run.status == "done"
    assert final_run.started_at is not None
    assert final_run.ended_at is not None


@pytest.mark.anyio
async def test_refine_copies_triggered_by_to_analyze_task_run(db: None, sample_article):
    """analyze TaskRun created by refine task copies triggered_by from refine TaskRun."""
    from app.tasks.refine import _refine_article_async
    from app.models import TaskRun

    task_run = TaskRun(
        task_type="refine",
        triggered_by="agent",
        triggered_by_label="workflow-123",
        entity_type="article",
        entity_id=sample_article.id,
        entity_name=sample_article.title,
        status="pending",
    )
    await task_run.insert()

    mock_analyze = MagicMock()
    mock_analyze.apply_async.return_value = MagicMock(id="celery-analyze-id")

    with (
        patch("app.core.agents.refiner.RefinerAgent.run", new=AsyncMock(return_value="# content")),
        patch("app.tasks.analyze.analyze_article_task", mock_analyze),
    ):
        await _refine_article_async(str(sample_article.id), str(task_run.id))

    # Check that an analyze TaskRun was created with correct triggered_by
    analyze_run = await TaskRun.find_one(
        TaskRun.entity_id == sample_article.id,
        TaskRun.task_type == "analyze",
    )
    assert analyze_run is not None
    assert analyze_run.triggered_by == "agent"
    assert analyze_run.triggered_by_label == "workflow-123"
