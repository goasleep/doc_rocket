"""Integration tests for /llm-model-configs API."""
import pytest
from httpx import AsyncClient

from app.models import LLMModelConfig


@pytest.fixture(autouse=True, scope="module")
async def clean_llm_model_configs(db: None):
    """Wipe LLMModelConfig collection before this test module runs."""
    await LLMModelConfig.delete_all()
    yield
    await LLMModelConfig.delete_all()


@pytest.mark.anyio
async def test_list_llm_model_configs_unauthenticated(client: AsyncClient, db: None):
    r = await client.get("/api/v1/llm-model-configs/")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_list_llm_model_configs_empty(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    r = await client.get("/api/v1/llm-model-configs/", headers=normal_user_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data


@pytest.mark.anyio
async def test_create_llm_model_config_requires_superuser(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    """Regular users cannot create model configs."""
    r = await client.post(
        "/api/v1/llm-model-configs/",
        json={
            "name": "My-Kimi",
            "provider_type": "kimi",
            "model_id": "moonshot-v1-32k",
            "api_key": "sk-test-key",
            "is_active": True,
        },
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403


@pytest.mark.anyio
async def test_create_and_get_llm_model_config(
    client: AsyncClient, superuser_token_headers: dict, db: None
):
    """Superuser can create a model config; API key is masked in response."""
    r = await client.post(
        "/api/v1/llm-model-configs/",
        json={
            "name": "Kimi-32k",
            "provider_type": "kimi",
            "model_id": "moonshot-v1-32k",
            "api_key": "sk-kimi-secret-key",
            "is_active": True,
        },
        headers=superuser_token_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Kimi-32k"
    assert data["provider_type"] == "kimi"
    assert data["model_id"] == "moonshot-v1-32k"
    assert data["is_active"] is True
    # API key should be masked, not exposed
    assert data["api_key_masked"] is not None
    assert "sk-kimi-secret-key" not in str(data.get("api_key_masked", ""))

    # Verify it appears in the list
    r2 = await client.get("/api/v1/llm-model-configs/", headers=superuser_token_headers)
    assert r2.status_code == 200
    names = [c["name"] for c in r2.json()["data"]]
    assert "Kimi-32k" in names


@pytest.mark.anyio
async def test_create_openai_compatible_config(
    client: AsyncClient, superuser_token_headers: dict, db: None
):
    """OpenAI-compatible configs require a base_url."""
    r = await client.post(
        "/api/v1/llm-model-configs/",
        json={
            "name": "Groq-Mixtral",
            "provider_type": "openai_compatible",
            "base_url": "https://api.groq.com/openai/v1",
            "model_id": "mixtral-8x7b-32768",
            "api_key": "gsk_test_key",
            "is_active": True,
        },
        headers=superuser_token_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["provider_type"] == "openai_compatible"
    assert data["base_url"] == "https://api.groq.com/openai/v1"
    assert data["model_id"] == "mixtral-8x7b-32768"


@pytest.mark.anyio
async def test_create_duplicate_name_returns_400(
    client: AsyncClient, superuser_token_headers: dict, db: None
):
    """Creating two configs with the same name should return 400."""
    payload = {
        "name": "Duplicate-Config",
        "provider_type": "kimi",
        "model_id": "moonshot-v1-32k",
        "api_key": "sk-key1",
        "is_active": True,
    }
    r1 = await client.post(
        "/api/v1/llm-model-configs/", json=payload, headers=superuser_token_headers
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/llm-model-configs/", json=payload, headers=superuser_token_headers
    )
    assert r2.status_code == 400
    assert "already exists" in r2.json()["detail"].lower()


@pytest.mark.anyio
async def test_update_llm_model_config(
    client: AsyncClient, superuser_token_headers: dict, db: None
):
    """Superuser can update model_id and other fields."""
    r = await client.post(
        "/api/v1/llm-model-configs/",
        json={
            "name": "Update-Test",
            "provider_type": "kimi",
            "model_id": "moonshot-v1-8k",
            "api_key": "sk-old-key",
            "is_active": True,
        },
        headers=superuser_token_headers,
    )
    assert r.status_code == 201
    config_id = r.json()["id"]

    # Update model_id and api_key
    r2 = await client.patch(
        f"/api/v1/llm-model-configs/{config_id}",
        json={"model_id": "moonshot-v1-32k", "api_key": "sk-new-key"},
        headers=superuser_token_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["model_id"] == "moonshot-v1-32k"
    # Masked key should be present and reflect a new value
    assert r2.json()["api_key_masked"] is not None


@pytest.mark.anyio
async def test_update_requires_superuser(
    client: AsyncClient, normal_user_token_headers: dict, superuser_token_headers: dict, db: None
):
    r = await client.post(
        "/api/v1/llm-model-configs/",
        json={
            "name": "Auth-Update-Test",
            "provider_type": "kimi",
            "model_id": "moonshot-v1-32k",
            "is_active": True,
        },
        headers=superuser_token_headers,
    )
    config_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/llm-model-configs/{config_id}",
        json={"model_id": "moonshot-v1-8k"},
        headers=normal_user_token_headers,
    )
    assert r2.status_code == 403


@pytest.mark.anyio
async def test_delete_llm_model_config(
    client: AsyncClient, superuser_token_headers: dict, db: None
):
    r = await client.post(
        "/api/v1/llm-model-configs/",
        json={
            "name": "Delete-Me",
            "provider_type": "kimi",
            "model_id": "moonshot-v1-32k",
            "api_key": "sk-key",
            "is_active": True,
        },
        headers=superuser_token_headers,
    )
    config_id = r.json()["id"]

    r2 = await client.delete(
        f"/api/v1/llm-model-configs/{config_id}",
        headers=superuser_token_headers,
    )
    assert r2.status_code == 204


@pytest.mark.anyio
async def test_delete_referenced_by_agent_returns_409(
    client: AsyncClient, superuser_token_headers: dict, normal_user_token_headers: dict, db: None
):
    """Deleting a model config referenced by an agent should return 409."""
    # Create the model config
    r = await client.post(
        "/api/v1/llm-model-configs/",
        json={
            "name": "referenced-model",
            "provider_type": "kimi",
            "model_id": "moonshot-v1-32k",
            "api_key": "sk-ref-key",
            "is_active": True,
        },
        headers=superuser_token_headers,
    )
    assert r.status_code == 201
    config_id = r.json()["id"]

    # Create an agent that references this config by name
    r2 = await client.post(
        "/api/v1/agents/",
        json={
            "name": "Ref Agent",
            "role": "custom",
            "responsibilities": "test",
            "system_prompt": "你是助手。",
            "model_config_name": "referenced-model",
            "workflow_order": 99,
        },
        headers=normal_user_token_headers,
    )
    assert r2.status_code == 201

    # Deleting the model config should fail with 409
    r3 = await client.delete(
        f"/api/v1/llm-model-configs/{config_id}",
        headers=superuser_token_headers,
    )
    assert r3.status_code == 409
    assert "referenced" in r3.json()["detail"].lower() or "agent" in r3.json()["detail"].lower()


@pytest.mark.anyio
async def test_delete_not_found(
    client: AsyncClient, superuser_token_headers: dict, db: None
):
    import uuid
    fake_id = str(uuid.uuid4())
    r = await client.delete(
        f"/api/v1/llm-model-configs/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_available_models_returns_active_configs(
    client: AsyncClient, superuser_token_headers: dict, normal_user_token_headers: dict, db: None
):
    """GET /agents/models/available returns active configs with API keys."""
    # Create an active config with a key
    await client.post(
        "/api/v1/llm-model-configs/",
        json={
            "name": "Available-Model",
            "provider_type": "kimi",
            "model_id": "moonshot-v1-32k",
            "api_key": "sk-available-key",
            "is_active": True,
        },
        headers=superuser_token_headers,
    )

    r = await client.get(
        "/api/v1/agents/models/available",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "models" in data
    names = [m["name"] for m in data["models"]]
    assert "Available-Model" in names
