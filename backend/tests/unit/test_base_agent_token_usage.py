"""Unit tests for BaseAgent token usage recording."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.agents.base import AgentContext, BaseAgent
from app.core.llm.base import ChatResponse, UsageData
from app.models.token_usage import TokenUsage, TokenUsageDaily


@pytest.mark.anyio
class TestBaseAgentTokenUsage:
    """Tests for BaseAgent token usage recording."""

    async def test_base_agent_records_token_usage_with_context(self, db):
        """Verify BaseAgent records token usage when context is provided."""
        # Create a mock agent config
        agent_config = MagicMock()
        agent_config.id = uuid.uuid4()
        agent_config.name = "TestAgent"
        agent_config.system_prompt = "You are a test agent."
        agent_config.max_iterations = 3
        agent_config.skills = []
        agent_config.tools = []
        agent_config.model_config_name = "test-model"

        agent = BaseAgent(agent_config=agent_config)

        # Mock the LLM client
        mock_llm = AsyncMock()
        mock_llm.model_name = "gpt-4"
        mock_llm.chat = AsyncMock(return_value=ChatResponse(
            content="Test response",
            usage=UsageData(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            ),
        ))

        with patch.object(agent, '_get_llm', return_value=mock_llm):
            with patch.object(agent, '_build_system_prompt', return_value="System prompt"):
                with patch.object(agent, '_build_tools_schema', return_value=None):
                    context = AgentContext(
                        entity_type="article",
                        entity_id=str(uuid.uuid4()),
                        operation="test_operation",
                    )

                    result = await agent.run("Test input", context=context)

        # Verify the response
        assert result == "Test response"

        # Verify token usage was recorded
        usage_records = await TokenUsage.find(
            TokenUsage.operation == "test_operation"
        ).to_list()

        assert len(usage_records) == 1
        usage = usage_records[0]
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.entity_type == "article"
        assert usage.operation == "test_operation"
        assert usage.agent_config_name == "TestAgent"

        # Clean up
        await usage.delete()
        await TokenUsageDaily.find(TokenUsageDaily.agent_config_id == agent_config.id).delete()

    async def test_base_agent_no_usage_without_context(self, db):
        """Verify BaseAgent does not record token usage when context is None."""
        # Create a mock agent config
        agent_config = MagicMock()
        agent_config.id = uuid.uuid4()
        agent_config.name = "TestAgent"
        agent_config.system_prompt = "You are a test agent."
        agent_config.max_iterations = 3
        agent_config.skills = []
        agent_config.tools = []
        agent_config.model_config_name = "test-model"

        agent = BaseAgent(agent_config=agent_config)

        # Mock the LLM client
        mock_llm = AsyncMock()
        mock_llm.model_name = "gpt-4"
        mock_llm.chat = AsyncMock(return_value=ChatResponse(
            content="Test response",
            usage=UsageData(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            ),
        ))

        with patch.object(agent, '_get_llm', return_value=mock_llm):
            with patch.object(agent, '_build_system_prompt', return_value="System prompt"):
                with patch.object(agent, '_build_tools_schema', return_value=None):
                    result = await agent.run("Test input", context=None)

        # Verify the response
        assert result == "Test response"

        # Verify no token usage was recorded
        usage_records = await TokenUsage.find(
            TokenUsage.agent_config_name == "TestAgent"
        ).to_list()

        assert len(usage_records) == 0

    async def test_base_agent_handles_missing_usage(self, db):
        """Verify BaseAgent handles missing usage data gracefully."""
        # Create a mock agent config
        agent_config = MagicMock()
        agent_config.id = uuid.uuid4()
        agent_config.name = "TestAgentMissing"
        agent_config.system_prompt = "You are a test agent."
        agent_config.max_iterations = 3
        agent_config.skills = []
        agent_config.tools = []
        agent_config.model_config_name = "test-model"

        agent = BaseAgent(agent_config=agent_config)

        # Mock the LLM client with no usage data (simulating streaming)
        mock_llm = AsyncMock()
        mock_llm.model_name = "gpt-4"
        mock_llm.chat = AsyncMock(return_value=ChatResponse(
            content="Test response",
            usage=None,  # No usage data
        ))

        with patch.object(agent, '_get_llm', return_value=mock_llm):
            with patch.object(agent, '_build_system_prompt', return_value="System prompt"):
                with patch.object(agent, '_build_tools_schema', return_value=None):
                    context = AgentContext(
                        entity_type="article",
                        entity_id=str(uuid.uuid4()),
                        operation="missing_usage_test",
                    )

                    result = await agent.run("Test input", context=context)

        # Verify the response
        assert result == "Test response"

        # Verify token usage was recorded with usage_missing flag
        usage_records = await TokenUsage.find(
            TokenUsage.operation == "missing_usage_test"
        ).to_list()

        assert len(usage_records) == 1
        usage = usage_records[0]
        assert usage.usage_missing is True
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

        # Clean up
        await usage.delete()
        await TokenUsageDaily.find(TokenUsageDaily.agent_config_id == agent_config.id).delete()

    async def test_agent_context_dataclass(self):
        """Verify AgentContext dataclass works correctly."""
        context = AgentContext(
            entity_type="article",
            entity_id="123e4567-e89b-12d3-a456-426614174000",
            operation="refine",
        )

        assert context.entity_type == "article"
        assert context.entity_id == "123e4567-e89b-12d3-a456-426614174000"
        assert context.operation == "refine"

        # Test default values
        empty_context = AgentContext()
        assert empty_context.entity_type == ""
        assert empty_context.entity_id is None
        assert empty_context.operation == ""
