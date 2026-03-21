"""Unit tests for OpenAICompatibleClient."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.llm.base import ChatResponse, ToolCall
from app.core.llm.kimi import KimiClient
from app.core.llm.openai_client import OpenAIClient
from app.core.llm.openai_compatible import OpenAICompatibleClient


def _make_text_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_tool_call_response(tool_id: str, name: str, args: dict) -> MagicMock:  # type: ignore[type-arg]
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = name
    tc.function.arguments = json.dumps(args)
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def kimi_client() -> KimiClient:
    return KimiClient(api_key="test-key")


async def test_chat_text_response(kimi_client: KimiClient) -> None:
    mock_resp = _make_text_response("Hello world")
    kimi_client._client.chat.completions.create = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

    result = await kimi_client.chat([{"role": "user", "content": "hi"}])

    assert isinstance(result, ChatResponse)
    assert result.content == "Hello world"
    assert result.tool_calls == []


async def test_chat_tool_call_response(kimi_client: KimiClient) -> None:
    mock_resp = _make_tool_call_response("call_123", "web_search", {"query": "AI news"})
    kimi_client._client.chat.completions.create = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

    result = await kimi_client.chat(
        [{"role": "user", "content": "search"}],
        tools=[{"type": "function", "function": {"name": "web_search"}}],
    )

    assert isinstance(result, ChatResponse)
    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_123"
    assert result.tool_calls[0].name == "web_search"
    assert result.tool_calls[0].arguments == {"query": "AI news"}


async def test_chat_json_object_mode(kimi_client: KimiClient) -> None:
    mock_resp = _make_text_response('{"key": "value"}')
    kimi_client._client.chat.completions.create = AsyncMock(return_value=mock_resp)  # type: ignore[attr-defined]

    result = await kimi_client.chat(
        [{"role": "user", "content": "return json"}],
        response_format={"type": "json_object"},
    )

    assert isinstance(result, ChatResponse)
    assert result.content is not None
    data = json.loads(result.content)
    assert data["key"] == "value"


def test_openai_client_inherits_compatible() -> None:
    client = OpenAIClient(api_key="test-key")
    assert isinstance(client, OpenAICompatibleClient)


def test_kimi_client_inherits_compatible() -> None:
    client = KimiClient(api_key="test-key")
    assert isinstance(client, OpenAICompatibleClient)
