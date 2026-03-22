"""Integration tests — fetch tasks create TaskRun records."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import Article, Source, TaskRun
from app.models.source import ApiConfig, FetchConfig


@pytest.fixture(autouse=True)
async def cleanup(db: None):
    yield
    await TaskRun.delete_all()
    await Article.delete_all()


@pytest.fixture
async def test_source(db: None) -> Source:
    source = Source(
        name="测试订阅源",
        type="api",
        url="https://example.com/api",
        api_config=ApiConfig(
            items_path="data",
            title_field="title",
            content_field="content",
            url_field="url",
        ),
        fetch_config=FetchConfig(interval_minutes=60, max_items_per_fetch=10),
        is_active=True,
    )
    await source.insert()
    return source


@pytest.mark.anyio
async def test_fetch_source_task_creates_fetch_task_run(db: None, test_source: Source, fake_redis_sync):
    """fetch_source_task creates a TaskRun(triggered_by=scheduler, entity_type=source)."""
    from app.tasks.fetch import _fetch_source_async

    with patch("app.tasks.fetch.FetcherAgent") as MockFetcher, \
         patch("app.tasks.fetch.analyze_article_task") as mock_analyze:
        mock_agent = AsyncMock()
        mock_agent.fetch_source.return_value = []
        MockFetcher.return_value = mock_agent
        mock_analyze.apply_async.return_value = MagicMock(id="fake-analyze-id")

        await _fetch_source_async(str(test_source.id))

    task_run = await TaskRun.find_one(
        TaskRun.entity_id == test_source.id,
        TaskRun.task_type == "fetch",
    )
    assert task_run is not None
    assert task_run.triggered_by == "scheduler"
    assert task_run.entity_type == "source"
    assert task_run.entity_id == test_source.id


@pytest.mark.anyio
async def test_fetch_source_task_done_on_success(db: None, test_source: Source, fake_redis_sync):
    """fetch_source_task marks fetch TaskRun as done on success."""
    from app.tasks.fetch import _fetch_source_async

    with patch("app.tasks.fetch.FetcherAgent") as MockFetcher, \
         patch("app.tasks.fetch.analyze_article_task") as mock_analyze:
        mock_agent = AsyncMock()
        mock_agent.fetch_source.return_value = []
        MockFetcher.return_value = mock_agent
        mock_analyze.apply_async.return_value = MagicMock(id="fake")

        await _fetch_source_async(str(test_source.id))

    task_run = await TaskRun.find_one(TaskRun.entity_id == test_source.id)
    assert task_run is not None
    assert task_run.status == "done"


@pytest.mark.anyio
async def test_fetch_source_task_failed_on_error(db: None, test_source: Source, fake_redis_sync):
    """fetch_source_task marks fetch TaskRun as failed on error."""
    from app.tasks.fetch import _fetch_source_async

    with patch("app.tasks.fetch.FetcherAgent") as MockFetcher:
        mock_agent = AsyncMock()
        mock_agent.fetch_source.side_effect = Exception("Network error")
        MockFetcher.return_value = mock_agent

        with pytest.raises(Exception, match="Network error"):
            await _fetch_source_async(str(test_source.id))

    task_run = await TaskRun.find_one(TaskRun.entity_id == test_source.id)
    assert task_run is not None
    assert task_run.status == "failed"
    assert task_run.error_message == "Network error"


@pytest.mark.anyio
async def test_fetch_source_task_creates_analyze_task_run_for_new_articles(
    db: None, test_source: Source, fake_redis_sync
):
    """For each new article, fetch_source_task should create an analyze TaskRun."""
    from app.tasks.fetch import _fetch_source_async

    new_articles = [
        {"title": "Article 1", "content": "Content 1", "url": "https://example.com/1"},
        {"title": "Article 2", "content": "Content 2", "url": "https://example.com/2"},
    ]
    mock_result = MagicMock(id="fake-analyze-id")

    with patch("app.tasks.fetch.FetcherAgent") as MockFetcher, \
         patch("app.tasks.fetch.analyze_article_task") as mock_analyze:
        mock_agent = AsyncMock()
        mock_agent.fetch_source.return_value = new_articles
        MockFetcher.return_value = mock_agent
        mock_analyze.apply_async.return_value = mock_result

        await _fetch_source_async(str(test_source.id))

    analyze_runs = await TaskRun.find(
        TaskRun.task_type == "analyze",
        TaskRun.triggered_by == "scheduler",
    ).to_list()
    assert len(analyze_runs) == 2
    for run in analyze_runs:
        assert run.celery_task_id == "fake-analyze-id"
        assert run.entity_type == "article"


@pytest.mark.anyio
async def test_fetch_source_task_no_analyze_task_run_when_no_new_articles(
    db: None, test_source: Source, fake_redis_sync
):
    """No analyze TaskRun should be created if all articles are already ingested."""
    existing = Article(
        source_id=test_source.id,
        title="Existing",
        content="content",
        url="https://example.com/existing",
        status="analyzed",
        input_type="fetched",
    )
    await existing.insert()

    from app.tasks.fetch import _fetch_source_async

    with patch("app.tasks.fetch.FetcherAgent") as MockFetcher, \
         patch("app.tasks.fetch.analyze_article_task") as mock_analyze:
        mock_agent = AsyncMock()
        mock_agent.fetch_source.return_value = [
            {"title": "Existing", "content": "content", "url": "https://example.com/existing"}
        ]
        MockFetcher.return_value = mock_agent
        mock_analyze.apply_async.return_value = MagicMock(id="fake")

        await _fetch_source_async(str(test_source.id))

    analyze_runs = await TaskRun.find(TaskRun.task_type == "analyze").to_list()
    assert len(analyze_runs) == 0


@pytest.mark.anyio
async def test_fetch_url_new_url_creates_task_runs(db: None, fake_redis_sync):
    """fetch_url_and_analyze_task creates fetch + analyze TaskRun for new URL."""
    from app.tasks.fetch import _fetch_url_and_analyze_async

    with patch("app.tasks.fetch.FetcherAgent") as MockFetcher, \
         patch("app.tasks.fetch.analyze_article_task") as mock_analyze:
        mock_agent = AsyncMock()
        mock_agent.fetch_url.return_value = {
            "title": "New Article",
            "content": "Article content for testing." * 5,
        }
        MockFetcher.return_value = mock_agent
        mock_analyze.apply_async.return_value = MagicMock(id="fake-analyze-id")

        article_id = await _fetch_url_and_analyze_async("https://example.com/new-article")

    assert article_id is not None
    article_uuid = uuid.UUID(article_id)

    fetch_run = await TaskRun.find_one(
        TaskRun.task_type == "fetch",
        TaskRun.entity_id == article_uuid,
    )
    assert fetch_run is not None
    assert fetch_run.status == "done"
    assert fetch_run.entity_type == "article"

    analyze_run = await TaskRun.find_one(
        TaskRun.task_type == "analyze",
        TaskRun.entity_id == article_uuid,
    )
    assert analyze_run is not None
    assert analyze_run.triggered_by == "manual"
    assert analyze_run.celery_task_id == "fake-analyze-id"


@pytest.mark.anyio
async def test_fetch_url_duplicate_url_creates_fetch_task_run_only(db: None, fake_redis_sync):
    """fetch_url_and_analyze_task on a known URL creates only a fetch TaskRun (no analyze)."""
    existing = Article(
        title="Existing Article",
        content="content",
        url="https://example.com/known",
        status="analyzed",
        input_type="manual",
    )
    await existing.insert()

    from app.tasks.fetch import _fetch_url_and_analyze_async

    with patch("app.tasks.fetch.FetcherAgent"):
        article_id = await _fetch_url_and_analyze_async("https://example.com/known")

    assert article_id == str(existing.id)

    fetch_run = await TaskRun.find_one(TaskRun.task_type == "fetch")
    assert fetch_run is not None
    assert fetch_run.entity_id == existing.id
    assert fetch_run.status == "done"

    analyze_runs = await TaskRun.find(TaskRun.task_type == "analyze").to_list()
    assert len(analyze_runs) == 0
