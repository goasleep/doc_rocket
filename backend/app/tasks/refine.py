"""Celery task for refining article content into clean Markdown."""
import uuid
from datetime import datetime, timezone


async def _refine_article_async(article_id: str, task_run_id: str) -> None:
    """Refine an article's content using RefinerAgent, then enqueue analysis.

    On success: sets content_md and refine_status="refined", enqueues analyze task.
    On failure: sets refine_status="failed", still enqueues analyze task (degrades to raw content).
    """
    from app.models import Article, TaskRun

    task_run = None
    if task_run_id:
        task_run = await TaskRun.find_one(TaskRun.id == uuid.UUID(task_run_id))
    article = await Article.find_one(Article.id == uuid.UUID(article_id))
    if not article:
        return

    # Mark as running
    article.refine_status = "refining"
    await article.save()

    if task_run:
        task_run.status = "running"
        task_run.started_at = datetime.now(timezone.utc)
        await task_run.save()

    triggered_by = task_run.triggered_by if task_run else "scheduler"
    triggered_by_label = task_run.triggered_by_label if task_run else None

    try:
        from app.core.agents.refiner import RefinerAgent
        from app.core.agents.base import AgentContext
        from app.models import AgentConfig

        agent_config = await AgentConfig.find_one(
            AgentConfig.role == "refiner",
            AgentConfig.is_active == True,
        )
        agent = RefinerAgent(agent_config=agent_config)

        # Create context for token usage tracking
        context = AgentContext(
            entity_type="article",
            entity_id=str(article.id),
            operation="refine",
        )

        # Build content with images for refinement
        content_with_images = agent.build_content_with_images(
            article.content, article.images
        )

        refined_md = await agent.run(
            content_with_images, context=context, images=article.images
        )

        article.content_md = refined_md
        article.refine_status = "refined"

        # Auto-extract title from first markdown heading if title is missing/untitled
        if not article.title or article.title.strip().lower() in ("untitled", ""):
            for line in refined_md.splitlines():
                if line.startswith("# "):
                    article.title = line[2:].strip()
                    break

        await article.save()

        if task_run:
            task_run.status = "done"
            task_run.ended_at = datetime.now(timezone.utc)
            await task_run.save()

    except Exception as exc:
        article.refine_status = "failed"
        await article.save()

        if task_run:
            task_run.status = "failed"
            task_run.error_message = str(exc)[:500]
            task_run.ended_at = datetime.now(timezone.utc)
            await task_run.save()

    # Always enqueue analysis (success: use content_md; failure: degrade to content)
    from app.models import TaskRun
    from app.tasks.analyze import analyze_article_task

    analyze_task_run = TaskRun(
        task_type="analyze",
        triggered_by=triggered_by,
        triggered_by_label=triggered_by_label,
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


from app.celery_app import celery_app, get_worker_loop


@celery_app.task(name="refine_article_task")
def refine_article_task(article_id: str, task_run_id: str) -> None:
    get_worker_loop().run_until_complete(_refine_article_async(article_id, task_run_id))
