"""Integration tests for /drafts API."""
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_drafts_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/drafts/")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_list_drafts(
    client: AsyncClient,
    superuser_token_headers: dict,
    sample_draft,
):
    r = await client.get("/api/v1/drafts/", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    ids = [d["id"] for d in data["data"]]
    assert str(sample_draft.id) in ids


@pytest.mark.anyio
async def test_get_draft(
    client: AsyncClient,
    superuser_token_headers: dict,
    sample_draft,
):
    r = await client.get(
        f"/api/v1/drafts/{sample_draft.id}", headers=superuser_token_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(sample_draft.id)
    assert data["title"] == sample_draft.title


@pytest.mark.anyio
async def test_get_draft_not_found(client: AsyncClient, superuser_token_headers: dict):
    import uuid
    r = await client.get(
        f"/api/v1/drafts/{uuid.uuid4()}", headers=superuser_token_headers
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_update_draft_content(
    client: AsyncClient,
    superuser_token_headers: dict,
    sample_draft,
):
    new_content = "# 更新后标题\n\n更新后的内容"
    r = await client.patch(
        f"/api/v1/drafts/{sample_draft.id}",
        json={"content": new_content},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == new_content
    # Edit history should be updated
    assert len(data["edit_history"]) >= 1


@pytest.mark.anyio
async def test_approve_draft(
    client: AsyncClient,
    superuser_token_headers: dict,
    sample_draft,
):
    r = await client.post(
        f"/api/v1/drafts/{sample_draft.id}/approve", headers=superuser_token_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved"


@pytest.mark.anyio
async def test_delete_draft(
    client: AsyncClient,
    superuser_token_headers: dict,
    sample_draft,
):
    r = await client.delete(
        f"/api/v1/drafts/{sample_draft.id}", headers=superuser_token_headers
    )
    assert r.status_code == 204
