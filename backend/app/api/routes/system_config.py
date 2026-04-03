"""System configuration routes — GET (masked) and PATCH (superuser only)."""
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SuperuserDep
from app.models import (
    SystemConfig,
    SystemConfigPublic,
    SystemConfigUpdate,
    LLMProviderPublic,
    LLMProvidersPublic,
    SearchConfig,
    OrchestratorConfig,
    WordCloudFilterConfig,
)

router = APIRouter(prefix="/system-config", tags=["system-config"])


def _mask_key(encrypted_key: str | None) -> str | None:
    if not encrypted_key:
        return None
    from app.core.encryption import decrypt_value, mask_api_key
    try:
        raw = decrypt_value(encrypted_key)
        return mask_api_key(raw)
    except Exception:
        return "***"


def _to_public(config: SystemConfig) -> SystemConfigPublic:
    return SystemConfigPublic(
        llm_providers=LLMProvidersPublic(
            kimi=LLMProviderPublic(
                api_key_masked=_mask_key(config.llm_providers.kimi.api_key_encrypted),
                default_model=config.llm_providers.kimi.default_model,
            ),
            claude=LLMProviderPublic(
                api_key_masked=_mask_key(config.llm_providers.claude.api_key_encrypted),
                default_model=config.llm_providers.claude.default_model,
            ),
            openai=LLMProviderPublic(
                api_key_masked=_mask_key(config.llm_providers.openai.api_key_encrypted),
                default_model=config.llm_providers.openai.default_model,
            ),
        ),
        scheduler=config.scheduler,
        analysis=config.analysis,
        writing=config.writing,
        search=SearchConfig(tavily_api_key=config.search.tavily_api_key if config.search else ""),
        orchestrator=config.orchestrator if config.orchestrator else OrchestratorConfig(),
        word_cloud_filter=config.word_cloud_filter if config.word_cloud_filter else WordCloudFilterConfig(),
    )


@router.get("/", response_model=SystemConfigPublic)
async def get_system_config(current_user: CurrentUser) -> Any:
    config = await SystemConfig.find_one()
    if not config:
        raise HTTPException(status_code=404, detail="System config not initialized")
    return _to_public(config)


@router.patch("/", response_model=SystemConfigPublic)
async def update_system_config(current_user: SuperuserDep, body: SystemConfigUpdate) -> Any:
    config = await SystemConfig.find_one()
    if not config:
        raise HTTPException(status_code=404, detail="System config not initialized")

    from app.core.encryption import encrypt_value

    if body.kimi_api_key is not None:
        config.llm_providers.kimi.api_key_encrypted = encrypt_value(body.kimi_api_key)
    if body.claude_api_key is not None:
        config.llm_providers.claude.api_key_encrypted = encrypt_value(body.claude_api_key)
    if body.openai_api_key is not None:
        config.llm_providers.openai.api_key_encrypted = encrypt_value(body.openai_api_key)
    if body.scheduler is not None:
        config.scheduler = body.scheduler
    if body.analysis is not None:
        config.analysis = body.analysis
    if body.writing is not None:
        config.writing = body.writing
    if body.search is not None:
        config.search = body.search
    if body.orchestrator is not None:
        config.orchestrator = body.orchestrator
    if body.word_cloud_filter is not None:
        config.word_cloud_filter = body.word_cloud_filter

    await config.save()
    return _to_public(config)
