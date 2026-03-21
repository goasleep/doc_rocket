"""Unit tests for ReviewerAgent."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from tests.fixtures.llm import MOCK_REVIEWER_RESPONSE


@pytest.mark.anyio
async def test_reviewer_output_structure():
    """ReviewerAgent output contains fact_check_flags, legal_notes, format_issues."""
    from app.core.agents.reviewer import ReviewerAgent

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_REVIEWER_RESPONSE)

    agent = ReviewerAgent()

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run("文章内容")

    parsed = json.loads(result)
    assert "fact_check_flags" in parsed
    assert "legal_notes" in parsed
    assert "format_issues" in parsed


@pytest.mark.anyio
async def test_reviewer_items_have_severity_and_description():
    """Each item in reviewer output has severity and description fields."""
    from app.core.agents.reviewer import ReviewerAgent

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_REVIEWER_RESPONSE)

    agent = ReviewerAgent()

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent.run("文章内容")

    parsed = json.loads(result)
    for key in ["fact_check_flags", "legal_notes", "format_issues"]:
        for item in parsed[key]:
            assert "severity" in item
            assert "description" in item
            assert item["severity"] in ("info", "warning", "error")
