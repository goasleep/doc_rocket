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


class AnalysisTraceResponse(BaseModel):
    article_id: uuid.UUID
    trace: list[dict[str, Any]]


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


@router.get("/{article_id}", response_model=ArticleAnalysisPublic)
async def get_analysis(current_user: CurrentUser, article_id: uuid.UUID) -> Any:
    """Get analysis by article ID."""
    analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == article_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/{article_id}/trace", response_model=AnalysisTraceResponse)
async def get_analysis_trace(current_user: CurrentUser, article_id: uuid.UUID) -> Any:
    """Get detailed analysis trace for an article."""
    analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == article_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    trace_data = []
    for step in analysis.trace:
        trace_data.append({
            "step_index": step.step_index,
            "step_name": step.step_name,
            "step_type": step.step_type,
            "input_summary": step.input_summary,
            "output_summary": step.output_summary,
            "duration_ms": step.duration_ms,
            "timestamp": step.timestamp.isoformat() if step.timestamp else None,
            "tool_calls": [tc.model_dump() for tc in step.tool_calls] if step.tool_calls else [],
            "parallel_group": step.parallel_group,
            "parallel_index": step.parallel_index,
        })

    return AnalysisTraceResponse(
        article_id=article_id,
        trace=trace_data,
    )


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
