"""Tests for analyze_article Celery task async logic."""
import pytest
from unittest.mock import AsyncMock, patch

from tests.fixtures.llm import MOCK_ANALYSIS_RESPONSE


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
