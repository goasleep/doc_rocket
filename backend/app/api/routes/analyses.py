"""Article analysis routes."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models import AnalysesPublic, Article, ArticleAnalysis, ArticleAnalysisPublic, Message
from app.tasks.analyze import analyze_article_task

router = APIRouter(prefix="/analyses", tags=["analyses"])


class TriggerAnalysisRequest(BaseModel):
    article_id: uuid.UUID


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

    analyze_article_task.apply_async(
        args=[str(article.id)],
        task_id=f"analyze_{article.id}",
    )

    return TriggerAnalysisResponse(
        message="Analysis task enqueued",
        article_id=str(article.id),
    )
