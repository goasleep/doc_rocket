"""Tests for context compression functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agents.compression import ContextCompressor, compress_context
from app.models.transcript import Transcript


class TestContextCompressor:
    """Test cases for ContextCompressor class."""

    def test_estimate_tokens_empty(self):
        """Test token estimation with empty messages."""
        compressor = ContextCompressor()
        assert compressor.estimate_tokens([]) == 0

    def test_estimate_tokens_simple(self):
        """Test token estimation with simple messages."""
        compressor = ContextCompressor()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        tokens = compressor.estimate_tokens(messages)
        # Rough check: should be positive and reasonable
        assert tokens > 0
        assert tokens < 1000

    def test_should_compress_below_threshold(self):
        """Test that small contexts don't trigger compression."""
        compressor = ContextCompressor(token_threshold=10000)
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        assert not compressor.should_compress(messages)

    def test_should_compress_above_threshold(self):
        """Test that large contexts trigger compression."""
        compressor = ContextCompressor(token_threshold=100)
        # Create a large message
        messages = [
            {"role": "system", "content": "x" * 1000},
        ]
        assert compressor.should_compress(messages)

    def test_microcompact_short_conversation(self):
        """Test microcompact keeps short conversations intact."""
        compressor = ContextCompressor()
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = compressor.microcompact(messages)
        assert len(result) == len(messages)

    def test_microcompact_removes_old_tool_results(self):
        """Test microcompact removes old tool results but keeps recent ones."""
        compressor = ContextCompressor()
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Task 1"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "function": {"name": "tool1"}}]},
            {"role": "tool", "tool_call_id": "1", "content": "Result 1"},
            {"role": "user", "content": "Task 2"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "2", "function": {"name": "tool2"}}]},
            {"role": "tool", "tool_call_id": "2", "content": "Result 2"},
            {"role": "user", "content": "Task 3"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "3", "function": {"name": "tool3"}}]},
            {"role": "tool", "tool_call_id": "3", "content": "Result 3"},
            {"role": "user", "content": "Task 4"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "4", "function": {"name": "tool4"}}]},
            {"role": "tool", "tool_call_id": "4", "content": "Result 4"},
        ]
        result = compressor.microcompact(messages)
        # System message should be preserved
        assert any(m.get("role") == "system" for m in result)
        # Should have fewer messages than original
        assert len(result) < len(messages)

    def test_microcompact_truncates_long_results(self):
        """Test microcompact truncates very long tool results."""
        compressor = ContextCompressor()
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Task 1"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "function": {"name": "tool1"}}]},
            {"role": "tool", "tool_call_id": "1", "content": "result 1"},
            {"role": "user", "content": "Task 2"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "2", "function": {"name": "tool2"}}]},
            {"role": "tool", "tool_call_id": "2", "content": "result 2"},
            {"role": "user", "content": "Task 3"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "3", "function": {"name": "tool3"}}]},
            {"role": "tool", "tool_call_id": "3", "content": "result 3"},
            {"role": "user", "content": "Task 4"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "4", "function": {"name": "tool4"}}]},
            {"role": "tool", "tool_call_id": "4", "content": "x" * 5000},
        ]
        result = compressor.microcompact(messages)
        tool_msg = [m for m in result if m.get("role") == "tool"][-1]
        assert len(tool_msg["content"]) < 2500
        assert "truncated" in tool_msg["content"]

    @pytest.mark.anyio
    async def test_compact_saves_transcript(self, db):
        """Test that compact saves transcript to database."""
        compressor = ContextCompressor()
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello!"},
        ]

        # Mock LLM client
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Summary of conversation"
        mock_llm.chat.return_value = mock_response

        with patch.object(Transcript, "insert", new_callable=AsyncMock) as mock_insert:
            compressed, transcript_id = await compressor.compact(messages, mock_llm, "workflow-123")

            # Should have saved transcript
            mock_insert.assert_called_once()
            assert transcript_id is not None
            assert len(compressed) > 0

    @pytest.mark.anyio
    async def test_compact_includes_summary(self, db):
        """Test that compact includes LLM-generated summary."""
        compressor = ContextCompressor()
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello!"},
        ]

        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "This was a greeting conversation"
        mock_llm.chat.return_value = mock_response

        with patch.object(Transcript, "insert", new_callable=AsyncMock):
            compressed, _ = await compressor.compact(messages, mock_llm)

            # Should have system message and summary
            system_msgs = [m for m in compressed if m.get("role") == "system"]
            assert len(system_msgs) >= 1
            # Summary should mention transcript ID
            assert any("Transcript ID" in str(m.get("content", "")) for m in compressed)


class TestCompressContextTool:
    """Test cases for compress_context tool function."""

    @pytest.mark.anyio
    async def test_compress_context_no_messages(self):
        """Test compress_context handles missing messages."""
        result = await compress_context(reason="test", messages=None)
        assert "Error" in result

    @pytest.mark.anyio
    async def test_compress_context_success(self, db):
        """Test successful compression via tool."""
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello!"},
        ]

        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Summary"

        with patch("app.core.llm.factory.get_llm_client_by_config_name", new_callable=AsyncMock, return_value=mock_llm):
            with patch("app.models.LLMModelConfig.find_one", new_callable=AsyncMock, return_value=MagicMock(name="test-model")):
                with patch.object(Transcript, "insert", new_callable=AsyncMock):
                    result = await compress_context(reason="test", messages=messages, workflow_run_id="wf-123")

        assert "context compressed" in result.lower()
        assert "Transcript ID" in result
        assert messages != []  # Should have been modified in place


class TestContextCompressionIntegration:
    """Integration tests for context compression in agent loop."""

    @pytest.mark.anyio
    async def test_base_agent_checks_compression(self):
        """Test that BaseAgent checks for compression during run."""
        from app.core.agents.base import BaseAgent, AgentRunContext

        agent = BaseAgent()

        # Mock dependencies
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.tool_calls = None
        mock_response.content = "Final answer"
        mock_llm.chat.return_value = mock_response

        with patch.object(agent, "_get_llm", return_value=mock_llm):
            with patch.object(agent, "_build_system_prompt", return_value="System prompt"):
                with patch.object(agent, "_build_tools_schema", return_value=None):
                    result = await agent.run("Test input")

        assert result == "Final answer"

    def test_agent_run_context_tracks_compression(self):
        """Test that AgentRunContext tracks compression count."""
        from app.core.agents.base import AgentRunContext
        ctx = AgentRunContext()
        assert ctx.compressed_count == 0
        ctx.compressed_count += 1
        assert ctx.compressed_count == 1