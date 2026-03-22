"""Celery task for AI analysis of articles."""
import asyncio
import uuid
from datetime import datetime, timezone


async def _analyze_article_async(article_id: str, task_run_id: str) -> None:
    """Analyze an article with the AnalyzerAgent.

    Idempotent: skips articles already in 'analyzing' or 'analyzed' status.
    Atomically transitions status raw → analyzing before proceeding.
    Updates the TaskRun status throughout the lifecycle.
    """
    from app.models import Article, ArticleAnalysis, TaskRun

    task_run = await TaskRun.find_one(TaskRun.id == uuid.UUID(task_run_id))

    article = await Article.find_one(Article.id == uuid.UUID(article_id))
    if not article:
        return

    # Idempotency guard: skip if already processing or done
    if article.status in ("analyzing", "analyzed"):
        return

    # Transition status to 'analyzing'
    article.status = "analyzing"
    await article.save()

    # Mark TaskRun as running
    if task_run:
        task_run.status = "running"
        task_run.started_at = datetime.now(timezone.utc)
        await task_run.save()

    try:
        from app.core.agents.analyzer import AnalyzerAgent
        from app.models import AgentConfig

        # Use the first active analyzer config or fallback defaults
        agent_config = await AgentConfig.find_one(
            AgentConfig.role == "writer",  # analyzer uses writing model defaults
            AgentConfig.is_active == True,  # noqa: E712
        )

        agent = AnalyzerAgent(agent_config=agent_config)
        analysis_data = await agent.run(article.content)

        # Save analysis
        analysis = ArticleAnalysis(
            article_id=article.id,
            **analysis_data,
        )
        await analysis.insert()

        # Mark article as analyzed
        article_doc = await Article.find_one(Article.id == uuid.UUID(article_id))
        if article_doc:
            article_doc.status = "analyzed"
            await article_doc.save()

        # Mark TaskRun as done
        if task_run:
            task_run.status = "done"
            task_run.ended_at = datetime.now(timezone.utc)
            await task_run.save()

    except Exception as exc:
        # Revert article status on failure so retries are possible
        article_doc = await Article.find_one(Article.id == uuid.UUID(article_id))
        if article_doc:
            article_doc.status = "raw"
            await article_doc.save()

        # Mark TaskRun as failed
        if task_run:
            task_run.status = "failed"
            task_run.error_message = str(exc)[:500]
            await task_run.save()

        raise


from app.celery_app import celery_app, get_worker_loop


@celery_app.task(name="analyze_article_task")
def analyze_article_task(article_id: str, task_run_id: str) -> None:
    get_worker_loop().run_until_complete(_analyze_article_async(article_id, task_run_id))
