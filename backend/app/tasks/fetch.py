"""Celery tasks for fetching articles from subscription sources."""
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app, get_worker_loop
from app.core.agents.fetcher import FetcherAgent
from app.core.redis_client import sync_redis
from app.tasks.analyze import analyze_article_task


async def _fetch_source_async(source_id: str) -> None:
    """Fetch articles from a subscription source.

    Uses a Redis distributed lock to prevent concurrent fetches of the same source.
    Skips articles with URLs already in the database.
    Enqueues analyze_article_task for each new article.
    """
    from app.models import Article, Source

    lock_key = f"fetch_lock:{source_id}"
    acquired = sync_redis.set(lock_key, 1, nx=True, ex=300)
    if not acquired:
        return  # Another worker is already fetching this source

    try:
        source = await Source.find_one(Source.id == uuid.UUID(source_id))
        if not source or not source.is_active:
            return

        agent = FetcherAgent()
        raw_articles = await agent.fetch_source(source)

        new_count = 0
        for raw in raw_articles:
            # Dedup by URL
            if raw.get("url"):
                existing = await Article.find_one(Article.url == raw["url"])
                if existing:
                    continue

            article = Article(
                source_id=source.id,
                title=raw.get("title", "Untitled"),
                content=raw.get("content", ""),
                url=raw.get("url"),
                author=raw.get("author"),
                published_at=raw.get("published_at"),
                status="raw",
                input_type="fetched",
            )
            await article.insert()
            new_count += 1

            # Enqueue analysis with unique task_id for dedup
            analyze_article_task.apply_async(
                args=[str(article.id)],
                task_id=f"analyze_{article.id}",
            )

        # Update last_fetched_at
        source.last_fetched_at = datetime.now(timezone.utc)
        await source.save()

    finally:
        sync_redis.delete(lock_key)


async def _fetch_url_and_analyze_async(url: str, user_id: str | None = None) -> str:
    """Fetch a single URL, create an Article, and enqueue analysis.

    Returns the article_id (existing or newly created).
    """
    from app.models import Article

    # Dedup: return existing article if URL already ingested
    existing = await Article.find_one(Article.url == url)
    if existing:
        return str(existing.id)

    agent = FetcherAgent()
    raw = await agent.fetch_url(url)

    article = Article(
        title=raw.get("title", "Untitled"),
        content=raw.get("content", ""),
        url=url,
        author=raw.get("author"),
        published_at=raw.get("published_at"),
        status="raw",
        input_type="manual",
    )
    await article.insert()

    analyze_article_task.apply_async(
        args=[str(article.id)],
        task_id=f"analyze_{article.id}",
    )

    return str(article.id)


@celery_app.task(name="fetch_source_task")
def fetch_source_task(source_id: str) -> None:
    get_worker_loop().run_until_complete(_fetch_source_async(source_id))


@celery_app.task(name="fetch_url_and_analyze_task")
def fetch_url_and_analyze_task(url: str, user_id: str | None = None) -> str:
    return get_worker_loop().run_until_complete(_fetch_url_and_analyze_async(url, user_id))
