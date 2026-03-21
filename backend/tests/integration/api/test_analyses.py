"""Integration tests for /analyses API."""
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from tests.fixtures.content import (  # noqa: F401
    sample_source,
    sample_article,
    analyzed_article,
)


@pytest.mark.anyio
async def test_list_analyses_by_quality_score(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    analyzed_article,
):
    """GET /analyses/ returns analyses sorted by quality_score descending."""
    r = await client.get("/api/v1/analyses/", headers=normal_user_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    if len(data["data"]) > 1:
        scores = [item["quality_score"] for item in data["data"]]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.anyio
async def test_get_analysis_by_id(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    analyzed_article,
):
    article, analysis = analyzed_article
    r = await client.get(
        f"/api/v1/analyses/{analysis.id}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["article_id"] == str(article.id)
    assert "quality_score" in data
    assert "hook_type" in data


@pytest.mark.anyio
async def test_get_analysis_not_found(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    import uuid
    r = await client.get(
        f"/api/v1/analyses/{uuid.uuid4()}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_trigger_analysis(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    sample_article,
):
    """POST /analyses/ triggers a new analysis task for the article."""
    with patch("app.api.routes.analyses.analyze_article_task") as mock_task:
        r = await client.post(
            "/api/v1/analyses/",
            json={"article_id": str(sample_article.id)},
            headers=normal_user_token_headers,
        )
    assert r.status_code == 202
    mock_task.apply_async.assert_called_once()


@pytest.mark.anyio
async def test_analyses_unauthenticated(client: AsyncClient, db: None):
    r = await client.get("/api/v1/analyses/")
    assert r.status_code == 401
