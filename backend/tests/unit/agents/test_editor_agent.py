"""Unit tests for EditorAgent."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from tests.fixtures.llm import MOCK_EDITOR_RESPONSE


@pytest.mark.anyio
async def test_editor_returns_three_title_candidates():
    """EditorAgent output always contains exactly 3 title_candidates."""
    from app.core.agents.editor import EditorAgent

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_EDITOR_RESPONSE)

    agent = EditorAgent()

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run("这是需要去AI味改写的文章内容。")

    parsed = json.loads(result)
    assert "title_candidates" in parsed
    assert len(parsed["title_candidates"]) == 3


@pytest.mark.anyio
async def test_editor_returns_changed_sections():
    """EditorAgent output contains changed_sections field."""
    from app.core.agents.editor import EditorAgent

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_EDITOR_RESPONSE)

    agent = EditorAgent()

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run("文章内容")

    parsed = json.loads(result)
    assert "changed_sections" in parsed
