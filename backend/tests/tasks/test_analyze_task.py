"""Tests for analyze_article Celery task async logic."""
import pytest
from unittest.mock import AsyncMock, patch

from tests.fixtures.llm import MOCK_ANALYSIS_RESPONSE
from tests.fixtures.content import sample_article, sample_source, analyzed_article  # noqa: F401


@pytest.mark.anyio
async def test_analyze_article_async_success(db: None, sample_article):
    """_analyze_article_async transitions article to 'analyzed' and creates ArticleAnalysis."""
    from app.tasks.analyze import _analyze_article_async
    from app.models import Article, ArticleAnalysis

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_ANALYSIS_RESPONSE)

    with patch("app.core.agents.analyzer.AnalyzerAgent._get_llm", return_value=mock_llm):
        await _analyze_article_async(str(sample_article.id))

    # Article status should be updated
    updated = await Article.find_one(Article.id == sample_article.id)
    assert updated is not None
    assert updated.status == "analyzed"

    # ArticleAnalysis should be created
    analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == sample_article.id)
    assert analysis is not None
    assert 0 <= analysis.quality_score <= 100


@pytest.mark.anyio
async def test_analyze_article_async_idempotent(db: None, analyzed_article):
    """_analyze_article_async skips articles already analyzed."""
    from app.tasks.analyze import _analyze_article_async
    from app.models import ArticleAnalysis

    article, _ = analyzed_article
    # Count analyses before
    count_before = await ArticleAnalysis.find(ArticleAnalysis.article_id == article.id).count()

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_ANALYSIS_RESPONSE)

    with patch("app.core.agents.analyzer.AnalyzerAgent._get_llm", return_value=mock_llm):
        await _analyze_article_async(str(article.id))

    # No new analysis should be created (already analyzed)
    count_after = await ArticleAnalysis.find(ArticleAnalysis.article_id == article.id).count()
    assert count_after == count_before


@pytest.mark.anyio
async def test_analyze_article_async_reverts_on_failure(db: None, sample_article):
    """_analyze_article_async reverts status to 'raw' on LLM failure."""
    from app.tasks.analyze import _analyze_article_async
    from app.models import Article

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(side_effect=RuntimeError("LLM API error"))

    with patch("app.core.agents.analyzer.AnalyzerAgent._get_llm", return_value=mock_llm):
        with pytest.raises(RuntimeError):
            await _analyze_article_async(str(sample_article.id))

    updated = await Article.find_one(Article.id == sample_article.id)
    assert updated is not None
    assert updated.status == "raw"


@pytest.mark.anyio
async def test_analyze_uses_content_md_when_available(db: None, sample_article):
    """When content_md is set, LLM receives content_md instead of content."""
    from app.tasks.analyze import _analyze_article_async

    sample_article.content_md = "# 精修版内容\n\n这是精修后的 Markdown。"
    sample_article.refine_status = "refined"
    await sample_article.save()

    captured_messages: list = []

    async def capture_chat(messages, **kwargs):
        captured_messages.extend(messages)
        return MOCK_ANALYSIS_RESPONSE

    mock_llm = AsyncMock()
    mock_llm.chat = capture_chat

    with patch("app.core.agents.analyzer.AnalyzerAgent._get_llm", return_value=mock_llm):
        await _analyze_article_async(str(sample_article.id))

    user_msg = next((m for m in captured_messages if m.get("role") == "user"), None)
    assert user_msg is not None
    assert "精修版内容" in user_msg["content"]


@pytest.mark.anyio
async def test_analyze_falls_back_to_content_when_no_content_md(db: None, sample_article):
    """When content_md is None, LLM receives original content."""
    from app.tasks.analyze import _analyze_article_async

    assert sample_article.content_md is None

    captured_messages: list = []

    async def capture_chat(messages, **kwargs):
        captured_messages.extend(messages)
        return MOCK_ANALYSIS_RESPONSE

    mock_llm = AsyncMock()
    mock_llm.chat = capture_chat

    with patch("app.core.agents.analyzer.AnalyzerAgent._get_llm", return_value=mock_llm):
        await _analyze_article_async(str(sample_article.id))

    user_msg = next((m for m in captured_messages if m.get("role") == "user"), None)
    assert user_msg is not None
    assert sample_article.content[:50] in user_msg["content"]


@pytest.mark.anyio
async def test_analyze_creates_trace_in_analysis(db: None, sample_article):
    """ArticleAnalysis.trace contains one AnalysisTraceStep with expected fields."""
    from app.tasks.analyze import _analyze_article_async
    from app.models import ArticleAnalysis

    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=MOCK_ANALYSIS_RESPONSE)

    with patch("app.core.agents.analyzer.AnalyzerAgent._get_llm", return_value=mock_llm):
        await _analyze_article_async(str(sample_article.id))

    analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == sample_article.id)
    assert analysis is not None
    assert len(analysis.trace) == 1

    step = analysis.trace[0]
    assert step.step_index == 0
    assert len(step.messages_sent) > 0
    assert step.raw_response != ""
    assert step.duration_ms >= 0
    assert step.timestamp is not None
