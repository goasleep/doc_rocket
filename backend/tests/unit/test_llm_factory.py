"""Unit tests for LLM factory."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.llm.base import LLMProviderNotConfiguredError
from app.core.llm.kimi import KimiClient


@pytest.mark.anyio
async def test_get_llm_client_kimi_with_key():
    """get_llm_client("kimi") returns KimiClient when given api_key directly."""
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


def test_claude_client_instantiation():
    from app.core.llm.claude_client import ClaudeClient
    client = ClaudeClient(api_key="sk-ant-fake", default_model="claude-sonnet-4-6")
    assert client._default_model == "claude-sonnet-4-6"


def test_openai_client_instantiation():
    from app.core.llm.openai_client import OpenAIClient
    client = OpenAIClient(api_key="sk-fake-openai", default_model="gpt-4o")
    assert client._default_model == "gpt-4o"
