"""Tests for ReactAnalyzerAgent."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.agents.react_analyzer import ReactAnalyzerAgent
from app.core.llm.base import ChatResponse
from app.models.quality_rubric import get_default_rubric


@pytest.mark.anyio
async def test_react_analyzer_returns_dict() -> None:
    """ReactAnalyzerAgent.run() returns a typed dict with analysis results."""
    agent = ReactAnalyzerAgent()

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=ChatResponse(
        content=json.dumps({
            "topic": "AI Technology",
            "core_ideas": ["AI is transforming industries"],
            "target_audience": "Tech professionals",
            "article_type": "opinion",
            "key_entities": ["AI", "Machine Learning"],
        }),
        tool_calls=[],
    ))

    with patch.object(agent, "_get_llm", return_value=mock_llm), \
         patch.object(agent, "_get_active_rubric", return_value=get_default_rubric()), \
         patch.object(agent, "_step_multidimensional_analysis", return_value=[
             {"dimension": "content_depth", "score": 80, "reasoning": "Good", "evidences": [], "improvement_suggestions": []},
             {"dimension": "readability", "score": 75, "reasoning": "Readable", "evidences": [], "improvement_suggestions": []},
             {"dimension": "originality", "score": 85, "reasoning": "Original", "evidences": [], "improvement_suggestions": []},
             {"dimension": "ai_flavor", "score": 70, "reasoning": "Natural", "evidences": [], "improvement_suggestions": []},
             {"dimension": "virality_potential", "score": 72, "reasoning": "Viral", "evidences": [], "improvement_suggestions": []},
         ]), \
         patch.object(agent, "_step_web_search", return_value=[]), \
         patch("app.core.agents.react_analyzer.dispatch_tool") as mock_dispatch:
        # Mock dispatch_tool for KB comparison
        mock_dispatch.return_value = "[]"

        result = await agent.run("Test article content", article_id="test-article-id")

    assert isinstance(result, dict)
    assert "quality_score" in result
    assert "quality_breakdown" in result
    assert "quality_score_details" in result


@pytest.mark.anyio
async def test_react_analyzer_step_understand() -> None:
    """Test the _step_understand method."""
    agent = ReactAnalyzerAgent()

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=ChatResponse(
        content=json.dumps({
            "content_type": "技术文章",
            "topic": "AI技术",
            "key_points": ["点1", "点2"],
            "complexity": "中等",
            "target_audience": "开发者",
        }),
        tool_calls=[],
    ))

    with patch.object(agent, "_get_llm", return_value=mock_llm):
        result = await agent._step_understand("Test content")

    assert isinstance(result, dict)
    assert result["topic"] == "AI技术"


@pytest.mark.anyio
async def test_react_analyzer_step_kb_comparison() -> None:
    """Test the _step_kb_comparison method."""
    agent = ReactAnalyzerAgent()

    # Mock dispatch_tool result
    mock_tool_result = json.dumps([
        {"article_id": "article-1", "title": "Similar Article", "relevance_score": 0.85}
    ])

    with patch("app.core.agents.react_analyzer.dispatch_tool", return_value=mock_tool_result):
        result = await agent._step_kb_comparison("Test content")

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Similar Article"


@pytest.mark.anyio
async def test_react_analyzer_step_scoring() -> None:
    """Test the _step_scoring_with_reasoning method."""
    agent = ReactAnalyzerAgent()

    dimension_results = [
        {
            "dimension": "content_depth",
            "score": 85,
            "reasoning": "内容深入",
            "evidences": [],
            "improvement_suggestions": [],
        }
    ]

    score_details, scores = await agent._step_scoring_with_reasoning(dimension_results, get_default_rubric())

    assert isinstance(score_details, list)
    assert len(score_details) == 1
    assert score_details[0].dimension == "content_depth"
    assert score_details[0].score == 85
    assert scores["content_depth"] == 85


@pytest.mark.anyio
async def test_react_analyzer_step_reflection() -> None:
    """Test the _step_reflection method."""
    agent = ReactAnalyzerAgent()

    from app.models import QualityScoreDetail
    score_details = [
        QualityScoreDetail(
            dimension="content_depth",
            score=85,
            weight=0.3,
            weighted_score=25.5,
            reasoning="内容深入",
            improvement_suggestions=["Add more examples"],
        )
    ]

    understanding = {"topic": "AI Technology"}

    summary, suggestions = await agent._step_reflection(score_details, understanding)

    assert isinstance(summary, str)
    assert isinstance(suggestions, list)


@pytest.mark.anyio
async def test_react_analyzer_run_integration() -> None:
    """Integration test for the full analysis workflow."""
    agent = ReactAnalyzerAgent()

    # Mock LLM responses for different steps
    llm_responses = [
        # Step 1: Understand (now includes legacy fields)
        ChatResponse(content=json.dumps({
            "topic": "AI Technology",
            "core_ideas": ["AI is transforming industries"],
            "target_audience": "Tech professionals",
            "article_type": "opinion",
            "key_entities": ["AI", "Machine Learning"],
            "hook_type": "好奇型",
            "framework": "AIDA",
            "emotional_triggers": ["好奇心", "紧迫感"],
            "structure": {
                "intro": "以问题引入AI的重要性",
                "body_sections": ["AI现状", "行业应用", "未来趋势"],
                "cta": "呼吁关注AI发展"
            },
            "style": {
                "tone": "专业",
                "formality": "半正式",
                "avg_sentence_length": 25
            }
        }), tool_calls=[]),
        # Step 4: Dimension analysis (called 5 times in parallel for default rubric dimensions)
        ChatResponse(content=json.dumps({
            "score": 80,
            "reasoning": "Good content",
            "evidences": [{"quote": "AI is", "context": "Introduction"}],
            "improvement_suggestions": ["Add more data"],
        }), tool_calls=[]),
        ChatResponse(content=json.dumps({
            "score": 75,
            "reasoning": "Readable",
            "evidences": [],
            "improvement_suggestions": [],
        }), tool_calls=[]),
        ChatResponse(content=json.dumps({
            "score": 85,
            "reasoning": "Original",
            "evidences": [],
            "improvement_suggestions": [],
        }), tool_calls=[]),
        ChatResponse(content=json.dumps({
            "score": 70,
            "reasoning": "Natural",
            "evidences": [],
            "improvement_suggestions": [],
        }), tool_calls=[]),
        ChatResponse(content=json.dumps({
            "score": 72,
            "reasoning": "Good potential",
            "evidences": [],
            "improvement_suggestions": [],
        }), tool_calls=[]),
        # Step 6: Reflection
        ChatResponse(content=json.dumps({
            "analysis_summary": "Overall good article",
            "improvement_suggestions": ["Add examples", "Improve structure"],
        }), tool_calls=[]),
    ]

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(side_effect=llm_responses)

    with patch.object(agent, "_get_llm", return_value=mock_llm), \
         patch.object(agent, "_step_web_search", return_value=[]), \
         patch("app.core.agents.react_analyzer.dispatch_tool") as mock_dispatch:
        # Mock tool responses
        mock_dispatch.return_value = "[]"

        result = await agent.run("Test article about AI", article_id="test-id")

    assert isinstance(result, dict)
    assert "quality_score" in result
    assert "quality_breakdown" in result
    assert "quality_score_details" in result
    assert "trace" in result
    assert len(result["trace"]) > 0
    # Verify legacy fields are populated
    assert result["hook_type"] == "好奇型"
    assert result["framework"] == "AIDA"
    assert result["emotional_triggers"] == ["好奇心", "紧迫感"]
    assert result["structure"]["intro"] == "以问题引入AI的重要性"
    assert result["structure"]["body_sections"] == ["AI现状", "行业应用", "未来趋势"]
    assert result["structure"]["cta"] == "呼吁关注AI发展"
    assert result["style"]["tone"] == "专业"
    assert result["style"]["formality"] == "半正式"
    assert result["style"]["avg_sentence_length"] == 25
