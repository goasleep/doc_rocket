"""Unit tests for RefinerAgent."""
import pytest
from unittest.mock import AsyncMock, patch

from app.core.llm.base import ChatResponse


MOCK_REFINED_RESPONSE = ChatResponse(
    content="# 测试文章标题\n\n这是整理后的 Markdown 内容。\n\n## 第一节\n\n段落内容。",
    tool_calls=[],
)


@pytest.mark.anyio
async def test_refiner_returns_nonempty_string():
    """RefinerAgent.run() returns a non-empty string from LLM response."""
    from app.core.agents.refiner import RefinerAgent

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_REFINED_RESPONSE)

    agent = RefinerAgent()

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run("导航栏 首页 关于 文章正文内容 版权所有 广告")

    assert isinstance(result, str)
    assert len(result) > 0
    assert "Markdown" in result or "标题" in result or "#" in result


@pytest.mark.anyio
async def test_refiner_truncates_long_content():
    """RefinerAgent truncates content over 16000 chars before sending to LLM."""
    from app.core.agents.refiner import RefinerAgent

    captured_messages: list = []

    async def capture_chat(messages, **kwargs):
        captured_messages.extend(messages)
        return MOCK_REFINED_RESPONSE

    mock_llm = AsyncMock()
    mock_llm.chat = capture_chat

    agent = RefinerAgent()
    long_content = "A" * 20000

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run(long_content)

    user_message = next((m for m in captured_messages if m.get("role") == "user"), None)
    assert user_message is not None
    # Content should be truncated (16000 + "[内容已截断...]" marker)
    assert len(user_message.get("content", "")) < 17000
    assert "[内容已截断...]" in user_message.get("content", "")
    assert isinstance(result, str)


@pytest.mark.anyio
async def test_refiner_fallback_on_empty_response():
    """RefinerAgent falls back to original input when LLM returns empty content."""
    from app.core.agents.refiner import RefinerAgent

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=ChatResponse(content="", tool_calls=[]))

    agent = RefinerAgent()
    original = "原始文章内容"

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run(original)

    assert result == original
