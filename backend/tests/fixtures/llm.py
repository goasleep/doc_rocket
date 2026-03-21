"""LLM mock fixtures for tests."""
import json
from unittest.mock import AsyncMock

import pytest

from app.core.llm.base import ChatResponse

MOCK_ANALYSIS_RESPONSE = ChatResponse(
    content=json.dumps({
        "quality_score": 82.0,
        "quality_breakdown": {
            "content_depth": 80,
            "readability": 85,
            "originality": 78,
            "virality_potential": 83,
        },
        "hook_type": "问题式",
        "framework": "AIDA",
        "emotional_triggers": ["焦虑", "好奇"],
        "key_phrases": ["爆款内容", "流量密码"],
        "keywords": ["内容营销", "AI写作", "爆品"],
        "structure": {
            "intro": "开篇提问，引发读者共鸣",
            "body_sections": ["分析问题", "提供方案", "案例论证"],
            "cta": "立即尝试，效果立竿见影",
        },
        "style": {
            "tone": "专业",
            "formality": "中等",
            "avg_sentence_length": 15,
        },
        "target_audience": "内容创作者、市场营销人员",
    }),
    tool_calls=[],
)

MOCK_EDITOR_RESPONSE = ChatResponse(
    content=json.dumps({
        "content": "这是经过去AI味处理后的文章内容。",
        "title_candidates": [
            "揭秘爆款内容的三大核心公式",
            "为什么你的文章没人看？这三点你没做到",
            "AI时代内容创作者的生存指南",
        ],
        "changed_sections": ["段落1", "段落3"],
    }),
    tool_calls=[],
)

MOCK_REVIEWER_RESPONSE = ChatResponse(
    content=json.dumps({
        "fact_check_flags": [
            {"severity": "info", "description": "数据引用建议注明来源"},
        ],
        "legal_notes": [],
        "format_issues": [
            {"severity": "warning", "description": "标题过长，建议控制在20字以内"},
        ],
    }),
    tool_calls=[],
)


@pytest.fixture
def mock_llm_client():
    """Returns an AsyncMock LLMClient that returns preset responses."""
    mock = AsyncMock()
    mock.chat = AsyncMock(return_value=MOCK_ANALYSIS_RESPONSE)
    return mock


@pytest.fixture
def mock_llm_client_editor():
    """Returns an AsyncMock LLMClient with Editor response."""
    mock = AsyncMock()
    mock.chat = AsyncMock(return_value=MOCK_EDITOR_RESPONSE)
    return mock


@pytest.fixture
def mock_llm_client_reviewer():
    """Returns an AsyncMock LLMClient with Reviewer response."""
    mock = AsyncMock()
    mock.chat = AsyncMock(return_value=MOCK_REVIEWER_RESPONSE)
    return mock
