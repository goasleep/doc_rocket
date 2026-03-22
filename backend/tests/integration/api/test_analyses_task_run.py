"""Integration tests — POST /analyses/ creates and updates TaskRun."""
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient

from app.models import Article, TaskRun


@pytest.fixture(autouse=True)
async def cleanup_task_runs():
    yield
    await TaskRun.delete_all()


@pytest.fixture
async def raw_article(db: None) -> Article:
    article = Article(
        title="测试文章",
        content="这是测试文章内容，用于验证TaskRun集成。" * 5,
        input_type="manual",
        status="raw",
    )
    await article.insert()
    return article


@pytest.mark.anyio
async def test_trigger_analysis_creates_task_run(
    client: AsyncClient, superuser_token_headers: dict, raw_article: Article
):
    """POST /analyses/ should create a TaskRun with status=pending."""
    mock_task = MagicMock()
    mock_task.id = "fake-celery-id"

    with patch("app.api.routes.analyses.analyze_article_task") as mock_celery:
        mock_celery.apply_async.return_value = mock_task
        r = await client.post(
            "/api/v1/analyses/",
            json={"article_id": str(raw_article.id)},
            headers=superuser_token_headers,
        )

    assert r.status_code == 202

    task_run = await TaskRun.find_one(TaskRun.entity_id == raw_article.id)
    assert task_run is not None
    assert task_run.status == "pending"
    assert task_run.entity_id == raw_article.id
    assert task_run.task_type == "analyze"


@pytest.mark.anyio
async def test_trigger_analysis_task_run_has_celery_id(
    client: AsyncClient, superuser_token_headers: dict, raw_article: Article
):
    """TaskRun.celery_task_id should be set after apply_async."""
    mock_task = MagicMock()
    mock_task.id = "celery-task-abc123"

    with patch("app.api.routes.analyses.analyze_article_task") as mock_celery:
        mock_celery.apply_async.return_value = mock_task
        r = await client.post(
            "/api/v1/analyses/",
            json={"article_id": str(raw_article.id)},
            headers=superuser_token_headers,
        )

    assert r.status_code == 202
    task_run = await TaskRun.find_one(TaskRun.entity_id == raw_article.id)
    assert task_run is not None
    assert task_run.celery_task_id == "celery-task-abc123"


@pytest.mark.anyio
async def test_trigger_analysis_rejects_scheduler_triggered_by(
    client: AsyncClient, superuser_token_headers: dict, raw_article: Article
):
    """triggered_by='scheduler' is not allowed via the API (422)."""
    r = await client.post(
        "/api/v1/analyses/",
        json={"article_id": str(raw_article.id), "triggered_by": "scheduler"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_trigger_analysis_default_triggered_by_manual(
    client: AsyncClient, superuser_token_headers: dict, raw_article: Article
):
    """Default triggered_by should be 'manual'."""
    mock_task = MagicMock()
    mock_task.id = "fake-id"

    with patch("app.api.routes.analyses.analyze_article_task") as mock_celery:
        mock_celery.apply_async.return_value = mock_task
        await client.post(
            "/api/v1/analyses/",
            json={"article_id": str(raw_article.id)},
            headers=superuser_token_headers,
        )

    task_run = await TaskRun.find_one(TaskRun.entity_id == raw_article.id)
    assert task_run is not None
    assert task_run.triggered_by == "manual"


@pytest.mark.anyio
async def test_trigger_analysis_agent_triggered_by_label(
    client: AsyncClient, superuser_token_headers: dict, raw_article: Article
):
    """triggered_by='agent' with triggered_by_label should be stored correctly."""
    mock_task = MagicMock()
    mock_task.id = "fake-id"

    with patch("app.api.routes.analyses.analyze_article_task") as mock_celery:
        mock_celery.apply_async.return_value = mock_task
        await client.post(
            "/api/v1/analyses/",
            json={
                "article_id": str(raw_article.id),
                "triggered_by": "agent",
                "triggered_by_label": "WriterAgent",
            },
            headers=superuser_token_headers,
        )

    task_run = await TaskRun.find_one(TaskRun.entity_id == raw_article.id)
    assert task_run is not None
    assert task_run.triggered_by == "agent"
    assert task_run.triggered_by_label == "WriterAgent"
