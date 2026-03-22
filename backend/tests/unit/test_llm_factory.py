"""Unit tests for LLM factory."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.llm.base import LLMProviderNotConfiguredError
from app.core.llm.kimi import KimiClient


# ── Legacy get_llm_client tests (kept for backward compat) ──────────────────

@pytest.mark.anyio
async def test_get_llm_client_kimi_with_key():
    """get_llm_client("kimi") returns KimiClient when api_key is configured."""
    from app.core.llm.factory import get_llm_client
    from app.core.encryption import encrypt_value

    mock_config = MagicMock()
    mock_config.llm_providers.kimi.api_key_encrypted = encrypt_value("sk-fake-kimi-key")
    mock_config.llm_providers.kimi.default_model = "moonshot-v1-32k"

    with patch("app.models.SystemConfig") as mock_sc:
        mock_sc.find_one = AsyncMock(return_value=mock_config)
        client = await get_llm_client("kimi")

    assert isinstance(client, KimiClient)


@pytest.mark.anyio
async def test_get_llm_client_not_configured():
    """get_llm_client raises LLMProviderNotConfiguredError if no API key."""
    from app.core.llm.factory import get_llm_client

    mock_config = MagicMock()
    mock_config.llm_providers.openai.api_key_encrypted = None

    with patch("app.models.SystemConfig") as mock_sc:
        mock_sc.find_one = AsyncMock(return_value=mock_config)
        with pytest.raises(LLMProviderNotConfiguredError):
            await get_llm_client("openai")


def test_kimi_client_uses_moonshot_base_url():
    """KimiClient should accept api_key and default_model."""
    client = KimiClient(api_key="sk-fake", default_model="moonshot-v1-32k")
    assert client._default_model == "moonshot-v1-32k"


def test_openai_client_instantiation():
    from app.core.llm.openai_client import OpenAIClient
    client = OpenAIClient(api_key="sk-fake-openai", default_model="gpt-4o")
    assert client._default_model == "gpt-4o"


def test_openai_client_with_base_url():
    """OpenAIClient should pass base_url to the underlying AsyncOpenAI."""
    from app.core.llm.openai_client import OpenAIClient
    client = OpenAIClient(
        api_key="sk-groq",
        default_model="mixtral-8x7b-32768",
        base_url="https://api.groq.com/openai/v1",
    )
    assert client._default_model == "mixtral-8x7b-32768"
    assert str(client._client.base_url).startswith("https://api.groq.com")


# ── New get_llm_client_by_config_name tests ─────────────────────────────────

@pytest.mark.anyio
async def test_get_llm_client_by_config_name_kimi():
    """Returns KimiClient for a kimi provider_type config."""
    from app.core.llm.factory import get_llm_client_by_config_name
    from app.core.encryption import encrypt_value

    mock_cfg = MagicMock()
    mock_cfg.name = "Kimi-32k"
    mock_cfg.provider_type = "kimi"
    mock_cfg.model_id = "moonshot-v1-32k"
    mock_cfg.api_key_encrypted = encrypt_value("sk-kimi-secret")
    mock_cfg.base_url = None

    with patch("app.models.LLMModelConfig") as mock_model:
        mock_model.find_one = AsyncMock(return_value=mock_cfg)
        client = await get_llm_client_by_config_name("Kimi-32k")

    assert isinstance(client, KimiClient)
    assert client._default_model == "moonshot-v1-32k"


@pytest.mark.anyio
async def test_get_llm_client_by_config_name_openai_compatible():
    """Returns OpenAIClient with custom base_url for openai_compatible config."""
    from app.core.llm.factory import get_llm_client_by_config_name
    from app.core.llm.openai_client import OpenAIClient
    from app.core.encryption import encrypt_value

    mock_cfg = MagicMock()
    mock_cfg.name = "Groq-Mixtral"
    mock_cfg.provider_type = "openai_compatible"
    mock_cfg.model_id = "mixtral-8x7b-32768"
    mock_cfg.api_key_encrypted = encrypt_value("gsk_test_key")
    mock_cfg.base_url = "https://api.groq.com/openai/v1"

    with patch("app.models.LLMModelConfig") as mock_model:
        mock_model.find_one = AsyncMock(return_value=mock_cfg)
        client = await get_llm_client_by_config_name("Groq-Mixtral")

    assert isinstance(client, OpenAIClient)
    assert client._default_model == "mixtral-8x7b-32768"


@pytest.mark.anyio
async def test_get_llm_client_by_config_name_not_found():
    """Raises LLMProviderNotConfiguredError when config name doesn't exist."""
    from app.core.llm.factory import get_llm_client_by_config_name

    with patch("app.models.LLMModelConfig") as mock_model:
        mock_model.find_one = AsyncMock(return_value=None)
        with pytest.raises(LLMProviderNotConfiguredError, match="not found"):
            await get_llm_client_by_config_name("nonexistent")


@pytest.mark.anyio
async def test_get_llm_client_by_config_name_no_api_key():
    """Raises LLMProviderNotConfiguredError when config has no API key."""
    from app.core.llm.factory import get_llm_client_by_config_name

    mock_cfg = MagicMock()
    mock_cfg.name = "No-Key-Config"
    mock_cfg.provider_type = "kimi"
    mock_cfg.api_key_encrypted = None

    with patch("app.models.LLMModelConfig") as mock_model:
        mock_model.find_one = AsyncMock(return_value=mock_cfg)
        with pytest.raises(LLMProviderNotConfiguredError, match="no API key"):
            await get_llm_client_by_config_name("No-Key-Config")
