"""Tests for _rewrite_section_async (direct call, not a Celery task)."""
from unittest.mock import AsyncMock, patch

import pytest

from tests.fixtures.content import (  # noqa: F401
    sample_draft,
    sample_agent_configs,
)


@pytest.mark.anyio
async def test_rewrite_section_returns_rewritten_text(
    db: None, sample_draft, sample_agent_configs
):
    """_rewrite_section_async returns non-empty text from the EditorAgent."""
    from app.tasks.rewrite import _rewrite_section_async

    expected = "这是经过去AI味处理的自然表达。"

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=f"  {expected}  ")

    with patch("app.tasks.rewrite.create_agent_for_config", return_value=mock_agent):
        result = await _rewrite_section_async(
            draft_id=str(sample_draft.id),
            selected_text="这是需要去AI味的文字。",
            context="上下文内容",
        )

    assert result == expected
    mock_agent.run.assert_called_once()
    call_args = mock_agent.run.call_args[0][0]
    assert "去AI味" in call_args
    assert "这是需要去AI味的文字。" in call_args


@pytest.mark.anyio
async def test_rewrite_section_draft_not_found(db: None, sample_agent_configs):
    """_rewrite_section_async raises ValueError for non-existent draft."""
    from app.tasks.rewrite import _rewrite_section_async
    import uuid

    with pytest.raises(ValueError, match="not found"):
        await _rewrite_section_async(
            draft_id=str(uuid.uuid4()),
            selected_text="some text",
        )
