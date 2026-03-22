"""Tests that AnalyzerAgent still returns dict (not affected by agentic loop)."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.agents.analyzer import AnalyzerAgent
from app.core.llm.base import ChatResponse


@pytest.mark.anyio
async def test_analyzer_returns_dict() -> None:
    """AnalyzerAgent.run() returns a typed dict, not a raw string."""
    agent = AnalyzerAgent()

    analysis_data = {
        "quality_score": 85,
        "quality_breakdown": {"content_depth": 80, "readability": 90, "originality": 85, "virality_potential": 85},
        "hook_type": "好奇型",
        "framework": "AIDA",
        "emotional_triggers": ["惊喜", "期待"],
        "key_phrases": ["革命性突破"],
        "keywords": ["AI", "未来"],
        "structure": {"intro": "开门见山", "body_sections": ["背景", "影响"], "cta": "订阅"},
        "style": {"tone": "严肃", "formality": "正式", "avg_sentence_length": 20},
        "target_audience": "科技从业者",
    }

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=ChatResponse(
        content=json.dumps(analysis_data),
        tool_calls=[],
    ))

    with patch.object(agent, "_get_llm", return_value=mock_llm), \
         patch.object(agent, "_system_prompt", return_value="你是分析专家", create=True):
        result = await agent.run("Test article content")

    assert isinstance(result, dict)
    assert result["quality_score"] == 85.0
    assert result["hook_type"] == "好奇型"
    assert result["framework"] == "AIDA"

    # AnalyzerAgent uses json_object response_format, not tool calls.
    # Confirm tools kwarg was not passed to llm.chat (or was None).
    call_kwargs = mock_llm.chat.call_args
    assert call_kwargs is not None
    passed_tools = call_kwargs.kwargs.get("tools")
    assert passed_tools is None
