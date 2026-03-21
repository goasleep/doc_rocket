"""Integration tests for /submit API."""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.anyio
async def test_submit_text_mode_creates_article(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    r = await client.post(
        "/api/v1/submit/",
        json={"mode": "text", "title": "测试标题", "content": "测试文章内容" * 10},
        headers=normal_user_token_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert "article_id" in data
    assert data["status"] == "raw"


@pytest.mark.anyio
async def test_submit_text_mode_triggers_analysis(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    """After text submit, analyze_article_task should be enqueued."""
    with patch("app.api.routes.submit.analyze_article_task") as mock_task:
        r = await client.post(
            "/api/v1/submit/",
            json={"mode": "text", "title": "分析触发测试", "content": "内容" * 20},
            headers=normal_user_token_headers,
        )
    assert r.status_code == 201
    mock_task.apply_async.assert_called_once()


@pytest.mark.anyio
async def test_submit_url_mode_enqueues_fetch(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    with patch("app.api.routes.submit.fetch_url_and_analyze_task") as mock_task:
        mock_task.apply_async.return_value = None
        r = await client.post(
            "/api/v1/submit/",
            json={"mode": "url", "url": "https://example.com/article"},
            headers=normal_user_token_headers,
        )
    assert r.status_code == 202
    mock_task.apply_async.assert_called_once()


@pytest.mark.anyio
async def test_submit_unauthenticated(client: AsyncClient):
    r = await client.post(
        "/api/v1/submit/",
        json={"mode": "text", "title": "t", "content": "c"},
    )
    assert r.status_code == 401


@pytest.mark.anyio
async def test_submit_text_mode_missing_content(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    r = await client.post(
        "/api/v1/submit/",
        json={"mode": "text", "title": "标题"},
        headers=normal_user_token_headers,
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_submit_url_mode_missing_url(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    r = await client.post(
        "/api/v1/submit/",
        json={"mode": "url"},
        headers=normal_user_token_headers,
    )
    assert r.status_code == 422
