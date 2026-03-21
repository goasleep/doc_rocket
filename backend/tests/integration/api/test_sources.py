"""Integration tests for /sources API."""
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_sources_requires_auth(client: AsyncClient):
    """GET /sources/ returns 401 without auth."""
    r = await client.get("/api/v1/sources/")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_list_sources_empty(client: AsyncClient, superuser_token_headers: dict):
    """GET /sources/ returns empty list initially."""
    r = await client.get("/api/v1/sources/", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data


@pytest.mark.anyio
async def test_create_source(client: AsyncClient, superuser_token_headers: dict):
    """POST /sources/ creates a new source."""
    payload = {
        "name": "Test Source",
        "type": "rss",
        "url": "https://example.com/feed.rss",
        "fetch_config": {"interval_minutes": 60, "max_items_per_fetch": 10},
    }
    r = await client.post(
        "/api/v1/sources/", json=payload, headers=superuser_token_headers
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Source"
    assert data["type"] == "rss"
    assert "id" in data


@pytest.mark.anyio
async def test_get_source_not_found(client: AsyncClient, superuser_token_headers: dict):
    """GET /sources/{id} returns 404 for unknown id."""
    import uuid
    r = await client.get(
        f"/api/v1/sources/{uuid.uuid4()}", headers=superuser_token_headers
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_delete_source(client: AsyncClient, superuser_token_headers: dict, sample_source):
    """DELETE /sources/{id} removes the source."""
    r = await client.delete(
        f"/api/v1/sources/{sample_source.id}", headers=superuser_token_headers
    )
    assert r.status_code == 204
