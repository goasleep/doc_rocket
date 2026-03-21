"""Integration tests for /articles API."""
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_articles_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/articles/")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_list_articles(client: AsyncClient, superuser_token_headers: dict, sample_article):
    r = await client.get("/api/v1/articles/", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    ids = [a["id"] for a in data["data"]]
    assert str(sample_article.id) in ids


@pytest.mark.anyio
async def test_get_article(client: AsyncClient, superuser_token_headers: dict, sample_article):
    r = await client.get(
        f"/api/v1/articles/{sample_article.id}", headers=superuser_token_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(sample_article.id)
    assert "content" in data


@pytest.mark.anyio
async def test_get_article_not_found(client: AsyncClient, superuser_token_headers: dict):
    import uuid
    r = await client.get(
        f"/api/v1/articles/{uuid.uuid4()}", headers=superuser_token_headers
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_archive_article(client: AsyncClient, superuser_token_headers: dict, sample_article):
    r = await client.delete(
        f"/api/v1/articles/{sample_article.id}", headers=superuser_token_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "archived"
