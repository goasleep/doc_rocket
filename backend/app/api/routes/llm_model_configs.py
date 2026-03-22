"""LLMModelConfig CRUD routes."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SuperuserDep
from app.core.encryption import decrypt_value, encrypt_value, mask_api_key
from app.models import (
    LLMModelConfig,
    LLMModelConfigCreate,
    LLMModelConfigPublic,
    LLMModelConfigsPublic,
    LLMModelConfigUpdate,
)

router = APIRouter(prefix="/llm-model-configs", tags=["llm-model-configs"])


def _to_public(cfg: LLMModelConfig) -> LLMModelConfigPublic:
    masked = None
    if cfg.api_key_encrypted:
        try:
            masked = mask_api_key(decrypt_value(cfg.api_key_encrypted))
        except Exception:
            masked = "***"
    return LLMModelConfigPublic(
        id=cfg.id,
        name=cfg.name,
        provider_type=cfg.provider_type,
        base_url=cfg.base_url,
        api_key_masked=masked,
        model_id=cfg.model_id,
        is_active=cfg.is_active,
        created_at=cfg.created_at,
    )


@router.get("/", response_model=LLMModelConfigsPublic)
async def list_llm_model_configs(current_user: CurrentUser) -> Any:
    import asyncio
    count, cfgs = await asyncio.gather(
        LLMModelConfig.count(),
        LLMModelConfig.find_all().sort("+created_at").to_list(),
    )
    return LLMModelConfigsPublic(data=[_to_public(c) for c in cfgs], count=count)


@router.post("/", response_model=LLMModelConfigPublic, status_code=201)
async def create_llm_model_config(
    current_user: SuperuserDep, body: LLMModelConfigCreate
) -> Any:
    existing = await LLMModelConfig.find_one(LLMModelConfig.name == body.name)
    if existing:
        raise HTTPException(status_code=400, detail="Model config name already exists")

    api_key_encrypted = None
    if body.api_key:
        api_key_encrypted = encrypt_value(body.api_key)

    cfg = LLMModelConfig(
        name=body.name,
        provider_type=body.provider_type,
        base_url=body.base_url,
        api_key_encrypted=api_key_encrypted,
        model_id=body.model_id,
        is_active=body.is_active,
    )
    await cfg.insert()
    return _to_public(cfg)


@router.patch("/{id}", response_model=LLMModelConfigPublic)
async def update_llm_model_config(
    current_user: SuperuserDep, id: uuid.UUID, body: LLMModelConfigUpdate
) -> Any:
    cfg = await LLMModelConfig.find_one(LLMModelConfig.id == id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Model config not found")

    update_data = body.model_dump(exclude_unset=True)

    # Handle api_key separately (encrypt it)
    if "api_key" in update_data:
        new_key = update_data.pop("api_key")
        cfg.api_key_encrypted = encrypt_value(new_key) if new_key else None

    # Check name uniqueness if being changed
    if "name" in update_data and update_data["name"] != cfg.name:
        existing = await LLMModelConfig.find_one(
            LLMModelConfig.name == update_data["name"]
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Model config name already exists"
            )

    for field, value in update_data.items():
        setattr(cfg, field, value)
    await cfg.save()
    return _to_public(cfg)


@router.delete("/{id}", status_code=204)
async def delete_llm_model_config(
    current_user: SuperuserDep, id: uuid.UUID
) -> None:
    cfg = await LLMModelConfig.find_one(LLMModelConfig.id == id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Model config not found")

    from app.models import AgentConfig
    referencing = await AgentConfig.find_one(AgentConfig.model_config_name == cfg.name)
    if referencing:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: agent '{referencing.name}' references this model config",
        )

    await cfg.delete()
