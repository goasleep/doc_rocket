"""Article analysis routes."""
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models import AnalysesPublic, Article, ArticleAnalysis, ArticleAnalysisPublic, Message, TaskRun
from app.tasks.analyze import analyze_article_task

router = APIRouter(prefix="/analyses", tags=["analyses"])


class TriggerAnalysisRequest(BaseModel):
    article_id: uuid.UUID
    triggered_by: Literal["manual", "agent"] = "manual"
    triggered_by_label: str | None = None


class TriggerAnalysisResponse(BaseModel):
    message: str
    article_id: str


@router.get("/", response_model=AnalysesPublic)
async def list_analyses(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    import asyncio
    count, analyses = await asyncio.gather(
        ArticleAnalysis.count(),
        ArticleAnalysis.find_all().sort("-quality_score").skip(skip).limit(limit).to_list(),
    )
    return AnalysesPublic(data=analyses, count=count)


@router.get("/{id}", response_model=ArticleAnalysisPublic)
async def get_analysis(current_user: CurrentUser, id: uuid.UUID) -> Any:
    analysis = await ArticleAnalysis.find_one(ArticleAnalysis.id == id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post("/", response_model=TriggerAnalysisResponse, status_code=202)
async def trigger_analysis(current_user: CurrentUser, body: TriggerAnalysisRequest) -> Any:
    """Manually trigger or re-trigger analysis for an article."""
    article = await Article.find_one(Article.id == body.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Reset status to allow re-analysis
    article.status = "raw"
    await article.save()

    # Create TaskRun before enqueuing
    task_run = TaskRun(
        task_type="analyze",
        triggered_by=body.triggered_by,
        triggered_by_label=body.triggered_by_label,
        entity_type="article",
        entity_id=article.id,
        entity_name=article.title,
        status="pending",
    )
    await task_run.insert()

    result = analyze_article_task.apply_async(
        args=[str(article.id)],
        kwargs={"task_run_id": str(task_run.id)},
        task_id=f"analyze_{article.id}",
    )
    task_run.celery_task_id = result.id
    await task_run.save()

    return TriggerAnalysisResponse(
        message="Analysis task enqueued",
        article_id=str(article.id),
    )
