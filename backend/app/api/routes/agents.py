"""AgentConfig CRUD routes."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.models import (
    AgentConfig,
    AgentConfigCreate,
    AgentConfigPublic,
    AgentConfigsPublic,
    AgentConfigUpdate,
    Message,
    WorkflowRun,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=AgentConfigsPublic)
async def list_agents(current_user: CurrentUser) -> Any:
    import asyncio
    count, agents = await asyncio.gather(
        AgentConfig.count(),
        AgentConfig.find_all().to_list(),
    )
    return AgentConfigsPublic(data=agents, count=count)


@router.post("/", response_model=AgentConfigPublic, status_code=201)
async def create_agent(current_user: CurrentUser, body: AgentConfigCreate) -> Any:
    raise HTTPException(
        status_code=403,
        detail="Agent creation is not allowed. Agents are code-defined and auto-synced on startup.",
    )


@router.get("/{id}", response_model=AgentConfigPublic)
async def get_agent(current_user: CurrentUser, id: uuid.UUID) -> Any:
    agent = await AgentConfig.find_one(AgentConfig.id == id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent config not found")
    return agent


@router.patch("/{id}", response_model=AgentConfigPublic)
async def update_agent(current_user: CurrentUser, id: uuid.UUID, body: AgentConfigUpdate) -> Any:
    agent = await AgentConfig.find_one(AgentConfig.id == id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent config not found")

    update_data = body.model_dump(exclude_unset=True)
    # Prompts and responsibilities are code-defined and immutable via API
    forbidden = {"system_prompt", "responsibilities"}
    for field in forbidden:
        update_data.pop(field, None)

    for field, value in update_data.items():
        setattr(agent, field, value)
    await agent.save()
    return agent


@router.delete("/{id}", status_code=204)
async def delete_agent(current_user: CurrentUser, id: uuid.UUID) -> None:
    agent = await AgentConfig.find_one(AgentConfig.id == id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent config not found")

    # Check for running workflows using this agent
    from beanie.operators import In
    running = await WorkflowRun.find_one(
        In(WorkflowRun.status, ["running", "pending"])
    )
    if running:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete agent config while workflows are running",
        )

    await agent.delete()


@router.get("/models/available")
async def get_available_models(current_user: CurrentUser) -> Any:
    """Return active LLMModelConfig names available for selection."""
    from app.models import LLMModelConfig

    cfgs = await LLMModelConfig.find(LLMModelConfig.is_active == True).to_list()  # noqa: E712
    return {
        "models": [
            {
                "name": c.name,
                "provider_type": c.provider_type,
                "model_id": c.model_id,
            }
            for c in cfgs
            if c.api_key_encrypted
        ]
    }
