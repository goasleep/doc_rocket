"""Integration tests — POST /workflows/ creates TaskRun linked to WorkflowRun."""
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient

from app.models import Article, TaskRun, WorkflowRun


@pytest.fixture(autouse=True)
async def cleanup_task_runs():
    yield
    await TaskRun.delete_all()
    await WorkflowRun.delete_all()


@pytest.fixture
async def raw_article(db: None) -> Article:
    article = Article(
        title="工作流测试文章",
        content="这是用于工作流任务集成测试的文章内容。" * 5,
        input_type="manual",
        status="analyzed",
    )
    await article.insert()
    return article


@pytest.mark.anyio
async def test_trigger_workflow_with_article_creates_task_run(
    client: AsyncClient, superuser_token_headers: dict, raw_article: Article
):
    """POST /workflows/ (with article_ids) creates TaskRun linked to WorkflowRun."""
    mock_task = MagicMock()
    mock_task.id = "fake-workflow-task"

    with patch("app.api.routes.workflows.writing_workflow_task") as mock_celery:
        mock_celery.delay.return_value = mock_task
        r = await client.post(
            "/api/v1/workflows/",
            json={"type": "writing", "article_ids": [str(raw_article.id)]},
            headers=superuser_token_headers,
        )

    assert r.status_code == 202
    run_id = r.json()["id"]

    import uuid
    task_run = await TaskRun.find_one(TaskRun.workflow_run_id == uuid.UUID(run_id))
    assert task_run is not None
    assert task_run.task_type == "workflow"
    assert task_run.entity_type == "article"
    assert task_run.entity_id == raw_article.id
    assert str(task_run.workflow_run_id) == run_id


@pytest.mark.anyio
async def test_trigger_workflow_topic_only_creates_task_run(
    client: AsyncClient, superuser_token_headers: dict
):
    """POST /workflows/ (topic-only) creates TaskRun with entity_type=None."""
    mock_task = MagicMock()
    mock_task.id = "fake-task"

    with patch("app.api.routes.workflows.writing_workflow_task") as mock_celery:
        mock_celery.delay.return_value = mock_task
        r = await client.post(
            "/api/v1/workflows/",
            json={"type": "writing", "article_ids": [], "topic": "AI写作趋势"},
            headers=superuser_token_headers,
        )

    assert r.status_code == 202
    run_id = r.json()["id"]

    import uuid
    task_run = await TaskRun.find_one(TaskRun.workflow_run_id == uuid.UUID(run_id))
    assert task_run is not None
    assert task_run.entity_type is None
    assert task_run.entity_id is None
    assert task_run.entity_name is not None
    assert "AI写作趋势" in task_run.entity_name


@pytest.mark.anyio
async def test_get_task_run_by_id_for_workflow(
    client: AsyncClient, superuser_token_headers: dict, raw_article: Article
):
    """TaskRun created for workflow should be retrievable via GET /task-runs/{id}."""
    mock_task = MagicMock()
    mock_task.id = "fake-task"

    with patch("app.api.routes.workflows.writing_workflow_task") as mock_celery:
        mock_celery.delay.return_value = mock_task
        r = await client.post(
            "/api/v1/workflows/",
            json={"type": "writing", "article_ids": [str(raw_article.id)]},
            headers=superuser_token_headers,
        )

    run_id = r.json()["id"]

    import uuid
    task_run = await TaskRun.find_one(TaskRun.workflow_run_id == uuid.UUID(run_id))
    assert task_run is not None

    r2 = await client.get(f"/api/v1/task-runs/{task_run.id}", headers=superuser_token_headers)
    assert r2.status_code == 200
    assert r2.json()["id"] == str(task_run.id)
