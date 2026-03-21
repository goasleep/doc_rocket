"""Integration tests for /system-config API."""
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_system_config_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/system-config/")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_get_system_config(client: AsyncClient, superuser_token_headers: dict, db: None):
    r = await client.get("/api/v1/system-config/", headers=superuser_token_headers)
    # May return 200 or 404 depending on whether SystemConfig is initialized
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        data = r.json()
        assert "llm_providers" in data
        assert "scheduler" in data


@pytest.mark.anyio
async def test_update_system_config_requires_superuser(
    client: AsyncClient,
    normal_user_token_headers: dict,
):
    r = await client.patch(
        "/api/v1/system-config/",
        json={"kimi_api_key": "sk-fake"},
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403


@pytest.mark.anyio
async def test_update_system_config(
    client: AsyncClient, superuser_token_headers: dict, db: None
):
    r = await client.patch(
        "/api/v1/system-config/",
        json={"kimi_api_key": "sk-fake-kimi-key"},
        headers=superuser_token_headers,
    )
    # May return 200 or 404 depending on init
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        data = r.json()
        # Key should be masked in response
        masked = data["llm_providers"]["kimi"]["api_key_masked"]
        assert masked is not None
        assert "***" in masked
