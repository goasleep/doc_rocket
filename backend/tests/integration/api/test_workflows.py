"""Integration tests for /workflows API."""
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_workflows_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/workflows/")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_trigger_workflow(
    client: AsyncClient,
    superuser_token_headers: dict,
    analyzed_article,
):
    """POST /workflows/ creates a WorkflowRun and returns 202."""
    article, _ = analyzed_article

    mock_task = MagicMock()
    mock_task.id = "fake-celery-task-id"

    with patch("app.api.routes.workflows.writing_workflow_task") as mock_celery:
        mock_celery.delay.return_value = mock_task
        r = await client.post(
            "/api/v1/workflows/",
            json={"type": "writing", "article_ids": [str(article.id)]},
            headers=superuser_token_headers,
        )

    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "pending"
    assert data["type"] == "writing"
    assert "id" in data


@pytest.mark.anyio
async def test_get_workflow_not_found(client: AsyncClient, superuser_token_headers: dict):
    import uuid
    r = await client.get(
        f"/api/v1/workflows/{uuid.uuid4()}", headers=superuser_token_headers
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_get_workflow(
    client: AsyncClient,
    superuser_token_headers: dict,
    sample_workflow_run,
):
    r = await client.get(
        f"/api/v1/workflows/{sample_workflow_run.id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(sample_workflow_run.id)
