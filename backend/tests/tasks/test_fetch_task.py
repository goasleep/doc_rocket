"""Tests for the fetch Celery task (calls _fetch_source_async directly)."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.fixtures.content import (  # noqa: F401
    sample_source,
    fake_redis_sync,
    sample_article,
)


@pytest.mark.anyio
async def test_fetch_creates_new_articles(db: None, sample_source, fake_redis_sync):
    """Two new articles are created and refine_article_task.apply_async called for each."""
    from app.tasks.fetch import _fetch_source_async
    from app.models import Article

    raw_articles = [
        {"title": "文章1", "content": "内容1", "url": "https://example.com/1"},
        {"title": "文章2", "content": "内容2", "url": "https://example.com/2"},
    ]

    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_source = AsyncMock(return_value=raw_articles)

    mock_refine = MagicMock()
    mock_refine.apply_async.return_value = MagicMock(id="fake-refine-id")

    with (
        patch("app.tasks.fetch.FetcherAgent", return_value=mock_fetcher),
        patch("app.tasks.fetch.refine_article_task", mock_refine),
    ):
        await _fetch_source_async(str(sample_source.id))

    articles = await Article.find(Article.source_id == sample_source.id).to_list()
    assert len(articles) == 2
    assert {a.url for a in articles} == {
        "https://example.com/1",
        "https://example.com/2",
    }
    assert all(a.status == "raw" for a in articles)
    assert mock_refine.apply_async.call_count == 2


@pytest.mark.anyio
async def test_fetch_deduplicates_existing_url(db: None, sample_source, fake_redis_sync):
    """Articles with already-existing URLs are skipped."""
    from app.tasks.fetch import _fetch_source_async
    from app.models import Article

    # Pre-create an article with a known URL
    existing = Article(
        source_id=sample_source.id,
        title="已存在",
        content="内容",
        url="https://example.com/existing",
        status="analyzed",
        input_type="fetched",
    )
    await existing.insert()

    raw_articles = [
        {"title": "新文章", "content": "内容", "url": "https://example.com/new"},
        {"title": "重复文章", "content": "内容", "url": "https://example.com/existing"},
    ]

    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_source = AsyncMock(return_value=raw_articles)

    mock_refine = MagicMock()
    mock_refine.apply_async.return_value = MagicMock(id="fake-refine-id")

    with (
        patch("app.tasks.fetch.FetcherAgent", return_value=mock_fetcher),
        patch("app.tasks.fetch.refine_article_task", mock_refine),
    ):
        await _fetch_source_async(str(sample_source.id))

    # Only 1 new article should be created (plus the pre-existing one = 2 total)
    all_articles = await Article.find(Article.source_id == sample_source.id).to_list()
    assert len(all_articles) == 2
    assert mock_refine.apply_async.call_count == 1


@pytest.mark.anyio
async def test_fetch_skips_inactive_source(db: None, sample_source, fake_redis_sync):
    """Inactive sources are skipped without calling FetcherAgent."""
    from app.tasks.fetch import _fetch_source_async

    sample_source.is_active = False
    await sample_source.save()

    mock_fetcher = AsyncMock()

    with patch("app.tasks.fetch.FetcherAgent", return_value=mock_fetcher):
        await _fetch_source_async(str(sample_source.id))

    mock_fetcher.fetch_source.assert_not_called()


@pytest.mark.anyio
async def test_fetch_respects_redis_lock(db: None, sample_source):
    """If the Redis lock is already held, skip the fetch entirely."""
    from app.tasks.fetch import _fetch_source_async

    mock_redis = MagicMock()
    mock_redis.set.return_value = None  # lock not acquired

    with (
        patch("app.tasks.fetch.sync_redis", mock_redis),
        patch("app.core.redis_client.sync_redis", mock_redis),
        patch("app.tasks.fetch.FetcherAgent") as mock_agent_class,
    ):
        await _fetch_source_async(str(sample_source.id))

    mock_agent_class.assert_not_called()


@pytest.mark.anyio
async def test_refetch_resets_refine_fields(db: None, sample_source, fake_redis_sync):
    """_refetch_article_async resets content_md=None and refine_status='pending' on refetch."""
    from app.tasks.fetch import _refetch_article_async
    from app.models import Article

    # Create article with existing refined content
    article = Article(
        source_id=sample_source.id,
        title="已精修文章",
        content="原始内容",
        url="https://example.com/refetch-test",
        status="analyzed",
        input_type="fetched",
        content_md="# 旧精修版\n\n旧内容",
        refine_status="refined",
    )
    await article.insert()

    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_url = AsyncMock(return_value={
        "title": "更新后标题",
        "content": "新内容",
    })

    mock_refine = MagicMock()
    mock_refine.apply_async.return_value = MagicMock(id="fake-refine-id")

    with (
        patch("app.tasks.fetch.FetcherAgent", return_value=mock_fetcher),
        patch("app.tasks.fetch.refine_article_task", mock_refine),
    ):
        await _refetch_article_async(str(article.id))

    updated = await Article.find_one(Article.id == article.id)
    assert updated is not None
    assert updated.content_md is None
    assert updated.refine_status == "pending"
    assert updated.status == "raw"

    # refine_article_task should be enqueued
    mock_refine.apply_async.assert_called_once()
