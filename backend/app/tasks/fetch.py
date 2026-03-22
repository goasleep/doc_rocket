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
    from app.models import Article, Source, TaskRun

    lock_key = f"fetch_lock:{source_id}"
    acquired = sync_redis.set(lock_key, 1, nx=True, ex=300)
    if not acquired:
        return  # Another worker is already fetching this source

    # Create fetch TaskRun at the start
    source = None
    fetch_task_run = None
    try:
        source = await Source.find_one(Source.id == uuid.UUID(source_id))
        if not source or not source.is_active:
            return

        fetch_task_run = TaskRun(
            task_type="fetch",
            triggered_by="scheduler",
            entity_type="source",
            entity_id=source.id,
            entity_name=source.name,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        await fetch_task_run.insert()

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

            # Create analyze TaskRun before enqueuing
            analyze_task_run = TaskRun(
                task_type="analyze",
                triggered_by="scheduler",
                entity_type="article",
                entity_id=article.id,
                entity_name=article.title,
                status="pending",
            )
            await analyze_task_run.insert()

            # Enqueue analysis with unique task_id for dedup
            result = analyze_article_task.apply_async(
                args=[str(article.id)],
                kwargs={"task_run_id": str(analyze_task_run.id)},
                task_id=f"analyze_{article.id}",
            )
            analyze_task_run.celery_task_id = result.id
            await analyze_task_run.save()

        # Update last_fetched_at and mark fetch TaskRun done
        source.last_fetched_at = datetime.now(timezone.utc)
        await source.save()

        fetch_task_run.status = "done"
        fetch_task_run.ended_at = datetime.now(timezone.utc)
        await fetch_task_run.save()

    except Exception as exc:
        if fetch_task_run:
            fetch_task_run.status = "failed"
            fetch_task_run.error_message = str(exc)[:500]
            await fetch_task_run.save()
        raise
    finally:
        sync_redis.delete(lock_key)


async def _fetch_url_and_analyze_async(url: str, user_id: str | None = None) -> str:
    """Fetch a single URL, create an Article, and enqueue analysis.

    Returns the article_id (existing or newly created).
    """
    from app.models import Article, TaskRun

    # Create fetch TaskRun at the start (entity unknown yet)
    fetch_task_run = TaskRun(
        task_type="fetch",
        triggered_by="manual",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    await fetch_task_run.insert()

    try:
        # Dedup: return existing article if URL already ingested
        existing = await Article.find_one(Article.url == url)
        if existing:
            fetch_task_run.entity_type = "article"
            fetch_task_run.entity_id = existing.id
            fetch_task_run.entity_name = existing.title
            fetch_task_run.status = "done"
            fetch_task_run.ended_at = datetime.now(timezone.utc)
            await fetch_task_run.save()
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

        # Back-fill fetch TaskRun with article info
        fetch_task_run.entity_type = "article"
        fetch_task_run.entity_id = article.id
        fetch_task_run.entity_name = article.title
        await fetch_task_run.save()

        # Create analyze TaskRun before enqueuing
        analyze_task_run = TaskRun(
            task_type="analyze",
            triggered_by="manual",
            entity_type="article",
            entity_id=article.id,
            entity_name=article.title,
            status="pending",
        )
        await analyze_task_run.insert()

        result = analyze_article_task.apply_async(
            args=[str(article.id)],
            kwargs={"task_run_id": str(analyze_task_run.id)},
            task_id=f"analyze_{article.id}",
        )
        analyze_task_run.celery_task_id = result.id
        await analyze_task_run.save()

        fetch_task_run.status = "done"
        fetch_task_run.ended_at = datetime.now(timezone.utc)
        await fetch_task_run.save()

        return str(article.id)

    except Exception as exc:
        fetch_task_run.status = "failed"
        fetch_task_run.error_message = str(exc)[:500]
        await fetch_task_run.save()
        raise


@celery_app.task(name="fetch_source_task")
def fetch_source_task(source_id: str) -> None:
    get_worker_loop().run_until_complete(_fetch_source_async(source_id))


@celery_app.task(name="fetch_url_and_analyze_task")
def fetch_url_and_analyze_task(url: str, user_id: str | None = None) -> str:
    return get_worker_loop().run_until_complete(_fetch_url_and_analyze_async(url, user_id))
