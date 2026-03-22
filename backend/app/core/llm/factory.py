"""LLM client factory — reads API keys from LLMModelConfig and instantiates the right client."""
from app.core.llm.base import LLMClient, LLMProviderNotConfiguredError

_KIMI_BASE_URL = "https://api.moonshot.cn/v1"


async def get_llm_client_by_config_name(name: str) -> LLMClient:
    """Return an instantiated LLM client for the named LLMModelConfig.

    Raises LLMProviderNotConfiguredError if the config is not found or has no API key.
    """
    from app.models import LLMModelConfig
    from app.core.encryption import decrypt_value

    cfg = await LLMModelConfig.find_one(LLMModelConfig.name == name)
    if not cfg:
        raise LLMProviderNotConfiguredError(f"model config '{name}' not found")
    if not cfg.api_key_encrypted:
        raise LLMProviderNotConfiguredError(f"model config '{name}' has no API key")

    api_key = decrypt_value(cfg.api_key_encrypted)

    if cfg.provider_type == "kimi":
        from app.core.llm.kimi import KimiClient
        return KimiClient(api_key=api_key, default_model=cfg.model_id)
    else:  # openai_compatible
        from app.core.llm.openai_client import OpenAIClient
        return OpenAIClient(
            api_key=api_key,
            default_model=cfg.model_id,
            base_url=cfg.base_url or None,
        )


async def get_llm_client(provider: str, model_id: str | None = None) -> LLMClient:
    """Legacy helper — reads API keys from SystemConfig.

    Kept for backward compatibility with code that still uses provider+model_id.
    Raises LLMProviderNotConfiguredError if the key is not set.
    """
    from app.models import SystemConfig
    from app.core.encryption import decrypt_value

    config = await SystemConfig.find_one()
    if not config:
        raise LLMProviderNotConfiguredError(provider)

    provider = provider.lower()

    if provider == "kimi":
        provider_cfg = config.llm_providers.kimi
        if not provider_cfg.api_key_encrypted:
            raise LLMProviderNotConfiguredError("kimi")
        api_key = decrypt_value(provider_cfg.api_key_encrypted)
        effective_model = model_id or provider_cfg.default_model or "moonshot-v1-32k"
        from app.core.llm.kimi import KimiClient
        return KimiClient(api_key=api_key, default_model=effective_model)

    elif provider == "openai":
        provider_cfg = config.llm_providers.openai
        if not provider_cfg.api_key_encrypted:
            raise LLMProviderNotConfiguredError("openai")
        api_key = decrypt_value(provider_cfg.api_key_encrypted)
        effective_model = model_id or provider_cfg.default_model or "gpt-4o"
        from app.core.llm.openai_client import OpenAIClient
        return OpenAIClient(api_key=api_key, default_model=effective_model)

    elif provider == "claude":
        raise LLMProviderNotConfiguredError("claude")

    else:
        raise LLMProviderNotConfiguredError(provider)
