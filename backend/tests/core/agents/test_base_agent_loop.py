"""Unit tests for BaseAgent agentic event loop."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.agents.base import BaseAgent
from app.core.llm.base import ChatResponse, ToolCall


def _make_mock_config(max_iterations: int = 5, tools: list = [], skills: list = []) -> MagicMock:
    cfg = MagicMock()
    cfg.model_provider = "kimi"
    cfg.model_id = "moonshot-v1-32k"
    cfg.system_prompt = "Test system prompt"
    cfg.max_iterations = max_iterations
    cfg.tools = tools
    cfg.skills = skills
    return cfg


def _text_response(content: str) -> ChatResponse:
    return ChatResponse(content=content, tool_calls=[])


def _tool_response(name: str, args: dict, tool_id: str = "call_1") -> ChatResponse:
    return ChatResponse(content=None, tool_calls=[ToolCall(id=tool_id, name=name, arguments=args)])


@pytest.mark.anyio
async def test_no_tools_returns_content_directly() -> None:
    """Without tools, agent returns LLM text directly."""
    agent = BaseAgent(agent_config=_make_mock_config(tools=[]))

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=_text_response("Final answer"))

    with patch.object(agent, "_get_llm", return_value=mock_llm), \
         patch.object(agent, "_build_system_prompt", return_value="Test system prompt"), \
         patch.object(agent, "_build_tools_schema", return_value=None):
        result = await agent.run("Hello")

    assert result == "Final answer"
    mock_llm.chat.assert_called_once()


@pytest.mark.anyio
async def test_tool_call_then_text() -> None:
    """Tool call followed by text response terminates loop."""
    agent = BaseAgent(agent_config=_make_mock_config(tools=["fetch_url"]))

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(side_effect=[
        _tool_response("fetch_url", {"url": "http://example.com"}),
        _text_response("Content from URL: summary"),
    ])

    mock_dispatch = AsyncMock(return_value="Page content here")

    with patch.object(agent, "_get_llm", return_value=mock_llm), \
         patch.object(agent, "_build_system_prompt", return_value="Test system prompt"), \
         patch.object(agent, "_build_tools_schema", return_value=[{"type": "function"}]), \
         patch("app.core.tools.registry.dispatch_tool", mock_dispatch):
        result = await agent.run("Fetch this URL")

    assert result == "Content from URL: summary"
    assert mock_llm.chat.call_count == 2
    mock_dispatch.assert_called_once_with("fetch_url", {"url": "http://example.com"})


@pytest.mark.anyio
async def test_max_iterations_circuit_breaker() -> None:
    """Loop terminates at max_iterations and returns last content."""
    agent = BaseAgent(agent_config=_make_mock_config(max_iterations=2, tools=["web_search"]))

    mock_llm = AsyncMock()
    # Always returns a tool call (never a final text answer), so max_iterations kicks in.
    mock_llm.chat = AsyncMock(side_effect=[
        ChatResponse(
            content="draft",
            tool_calls=[ToolCall(id="call_0", name="web_search", arguments={"query": "q"})],
        ),
        ChatResponse(
            content="draft2",
            tool_calls=[ToolCall(id="call_1", name="web_search", arguments={"query": "q"})],
        ),
    ])

    mock_dispatch = AsyncMock(return_value="search results")

    with patch.object(agent, "_get_llm", return_value=mock_llm), \
         patch.object(agent, "_build_system_prompt", return_value="Test system prompt"), \
         patch.object(agent, "_build_tools_schema", return_value=[{"type": "function"}]), \
         patch("app.core.tools.registry.dispatch_tool", mock_dispatch):
        result = await agent.run("Search for something")

    # Returns last seen content after max_iterations exhausted
    assert result in ("draft", "draft2", "")
    assert mock_llm.chat.call_count == 2  # exactly max_iterations


@pytest.mark.anyio
async def test_consecutive_tool_failure_circuit_breaker() -> None:
    """Same tool failing 3 times terminates loop."""
    agent = BaseAgent(agent_config=_make_mock_config(max_iterations=10, tools=["web_search"]))

    mock_llm = AsyncMock()
    # Always calls web_search; the 4th response would be a text answer but should never be reached.
    responses = [
        _tool_response("web_search", {"query": "q"}, f"call_{i}")
        for i in range(3)
    ]
    mock_llm.chat = AsyncMock(side_effect=responses + [_text_response("done")])

    # Tool always returns an error string to trigger the circuit breaker
    mock_dispatch = AsyncMock(return_value="Tool 'web_search' error: connection refused")

    with patch.object(agent, "_get_llm", return_value=mock_llm), \
         patch.object(agent, "_build_system_prompt", return_value="Test system prompt"), \
         patch.object(agent, "_build_tools_schema", return_value=[{"type": "function"}]), \
         patch("app.core.tools.registry.dispatch_tool", mock_dispatch):
        result = await agent.run("Search something")

    # Loop terminated after 3 consecutive failures — 4th LLM call never happens
    assert mock_llm.chat.call_count == 3
