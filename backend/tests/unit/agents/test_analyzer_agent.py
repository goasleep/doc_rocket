"""Unit tests for AnalyzerAgent."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from tests.fixtures.llm import MOCK_ANALYSIS_RESPONSE


@pytest.mark.anyio
async def test_analyzer_parses_valid_response():
    """AnalyzerAgent correctly parses LLM JSON response into a dict."""
    from app.core.agents.analyzer import AnalyzerAgent

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_ANALYSIS_RESPONSE)

    agent = AnalyzerAgent()

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run("这是一篇测试文章内容。" * 100)

    assert result is not None
    assert 0 <= result["quality_score"] <= 100
    assert result["hook_type"]
    assert result["framework"]
    assert isinstance(result["emotional_triggers"], list)


@pytest.mark.anyio
async def test_analyzer_truncates_long_content():
    """AnalyzerAgent truncates content over 12000 chars before sending to LLM."""
    from app.core.agents.analyzer import AnalyzerAgent

    captured_messages: list = []

    async def capture_chat(messages, **kwargs):
        captured_messages.extend(messages)
        return MOCK_ANALYSIS_RESPONSE

    mock_llm = AsyncMock()
    mock_llm.chat = capture_chat

    agent = AnalyzerAgent()
    long_content = "A" * 20000

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        await agent.run(long_content)

    user_message = next((m for m in captured_messages if m.get("role") == "user"), None)
    assert user_message is not None
    assert len(user_message.get("content", "")) < 15000


@pytest.mark.anyio
async def test_analyzer_quality_score_in_range():
    """Quality score must be between 0 and 100."""
    from app.core.agents.analyzer import AnalyzerAgent

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_ANALYSIS_RESPONSE)
    agent = AnalyzerAgent()

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run("测试内容")

    assert 0 <= result["quality_score"] <= 100
