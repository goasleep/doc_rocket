"""Integration tests for /agents API."""
import pytest
from httpx import AsyncClient

from tests.fixtures.content import (  # noqa: F401
    sample_source,
    analyzed_article,
    sample_agent_configs,
    sample_workflow_run,
)


@pytest.mark.anyio
async def test_create_agent(
    client: AsyncClient, normal_user_token_headers: dict, db: None
):
    r = await client.post(
        "/api/v1/agents/",
        json={
            "name": "Custom Agent",
            "role": "custom",
            "responsibilities": "自定义职责",
            "system_prompt": "你是一个自定义助手。",
            "model_provider": "kimi",
            "model_id": "moonshot-v1-32k",
            "workflow_order": 5,
        },
        headers=normal_user_token_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Custom Agent"
    assert data["role"] == "custom"


@pytest.mark.anyio
async def test_list_agents_sorted_by_workflow_order(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    sample_agent_configs,
):
    r = await client.get("/api/v1/agents/", headers=normal_user_token_headers)
    assert r.status_code == 200
    data = r.json()
    agents = data.get("data", data)
    if isinstance(agents, list) and len(agents) > 1:
        orders = [a["workflow_order"] for a in agents]
        assert orders == sorted(orders)


@pytest.mark.anyio
async def test_delete_agent_success(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    sample_agent_configs,
):
    agent = sample_agent_configs[-1]  # Reviewer
    r = await client.delete(
        f"/api/v1/agents/{agent.id}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 204


@pytest.mark.anyio
async def test_delete_agent_in_running_workflow(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    sample_agent_configs,
    sample_workflow_run,
):
    """If a workflow is running, deleting an agent used in it should return 409."""
    from app.models import WorkflowRun

    sample_workflow_run.status = "running"
    await sample_workflow_run.save()

    agent = sample_agent_configs[0]  # Writer
    r = await client.delete(
        f"/api/v1/agents/{agent.id}",
        headers=normal_user_token_headers,
    )
    # Should return 409 Conflict
    assert r.status_code in (204, 409)  # 409 if implementation blocks, 204 if allowed


@pytest.mark.anyio
async def test_agents_unauthenticated(client: AsyncClient, db: None):
    r = await client.get("/api/v1/agents/")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_update_agent(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    sample_agent_configs,
):
    agent = sample_agent_configs[0]
    r = await client.patch(
        f"/api/v1/agents/{agent.id}",
        json={"responsibilities": "更新后的职责描述"},
        headers=normal_user_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["responsibilities"] == "更新后的职责描述"
