"""Unit tests for OpenAI-compatible LLM client usage extraction."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm.openai_compatible import OpenAICompatibleClient
from app.core.llm.base import UsageData


class TestOpenAICompatibleClientUsage:
    """Tests for usage data extraction from OpenAI-compatible responses."""

    @pytest.mark.anyio
    async def test_chat_extracts_usage_from_response(self):
        """Verify that usage data is extracted from API response."""
        client = OpenAICompatibleClient.__new__(OpenAICompatibleClient)
        client._default_model = "gpt-4"
        client._client = MagicMock()

        # Create mock response with usage data
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 150
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 200

        mock_message = MagicMock()
        mock_message.content = "Test response"
        mock_message.tool_calls = None
        mock_message.reasoning_content = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat(messages=[{"role": "user", "content": "Hello"}])

        assert result.usage is not None
        assert result.usage.prompt_tokens == 150
        assert result.usage.completion_tokens == 50
        assert result.usage.total_tokens == 200

    @pytest.mark.anyio
    async def test_chat_handles_missing_usage(self):
        """Verify that missing usage data is handled gracefully."""
        client = OpenAICompatibleClient.__new__(OpenAICompatibleClient)
        client._default_model = "gpt-4"
        client._client = MagicMock()

        # Create mock response without usage data (e.g., streaming response)
        mock_response = MagicMock()
        mock_response.usage = None

        mock_message = MagicMock()
        mock_message.content = "Test response"
        mock_message.tool_calls = None
        mock_message.reasoning_content = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat(messages=[{"role": "user", "content": "Hello"}])

        assert result.usage is None

    @pytest.mark.anyio
    async def test_chat_handles_zero_tokens(self):
        """Verify that zero token counts are handled correctly."""
        client = OpenAICompatibleClient.__new__(OpenAICompatibleClient)
        client._default_model = "gpt-4"
        client._client = MagicMock()

        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 0
        mock_response.usage.completion_tokens = 0
        mock_response.usage.total_tokens = 0

        mock_message = MagicMock()
        mock_message.content = ""
        mock_message.tool_calls = None
        mock_message.reasoning_content = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat(messages=[{"role": "user", "content": ""}])

        assert result.usage is not None
        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 0
        assert result.usage.total_tokens == 0

    @pytest.mark.anyio
    async def test_chat_preserves_other_response_fields(self):
        """Verify that usage extraction doesn't break other response fields."""
        client = OpenAICompatibleClient.__new__(OpenAICompatibleClient)
        client._default_model = "gpt-4"
        client._client = MagicMock()

        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 25
        mock_response.usage.total_tokens = 125

        mock_message = MagicMock()
        mock_message.content = "Test content"
        mock_message.tool_calls = None
        mock_message.reasoning_content = "Thinking..."

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat(messages=[{"role": "user", "content": "Hello"}])

        assert result.content == "Test content"
        assert result.reasoning_content == "Thinking..."
        assert result.tool_calls == []
        assert result.usage.prompt_tokens == 100


class TestUsageDataDataclass:
    """Tests for UsageData dataclass."""

    def test_usage_data_creation(self):
        """Verify UsageData can be created with all fields."""
        usage = UsageData(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_usage_data_equality(self):
        """Verify UsageData equality comparison."""
        usage1 = UsageData(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        usage2 = UsageData(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        usage3 = UsageData(prompt_tokens=200, completion_tokens=50, total_tokens=250)

        assert usage1 == usage2
        assert usage1 != usage3
