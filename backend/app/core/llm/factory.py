"""LLM client factory — reads API keys from SystemConfig and instantiates the right client."""
from app.core.llm.base import LLMClient, LLMProviderNotConfiguredError


async def get_llm_client(provider: str, model_id: str | None = None) -> LLMClient:
    """Return an instantiated LLM client for the given provider.

    Reads the encrypted API key from SystemConfig and decrypts it.
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

    elif provider == "claude":
        provider_cfg = config.llm_providers.claude
        if not provider_cfg.api_key_encrypted:
            raise LLMProviderNotConfiguredError("claude")
        api_key = decrypt_value(provider_cfg.api_key_encrypted)
        effective_model = model_id or provider_cfg.default_model or "claude-sonnet-4-6"
        from app.core.llm.claude_client import ClaudeClient
        return ClaudeClient(api_key=api_key, default_model=effective_model)

    elif provider == "openai":
        provider_cfg = config.llm_providers.openai
        if not provider_cfg.api_key_encrypted:
            raise LLMProviderNotConfiguredError("openai")
        api_key = decrypt_value(provider_cfg.api_key_encrypted)
        effective_model = model_id or provider_cfg.default_model or "gpt-4o"
        from app.core.llm.openai_client import OpenAIClient
        return OpenAIClient(api_key=api_key, default_model=effective_model)

    else:
        raise LLMProviderNotConfiguredError(provider)
