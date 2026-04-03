"""Article analysis routes."""
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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


class AnalyzeContentRequest(BaseModel):
    """Request to analyze content without persisting to database."""
    title: str = Field(..., description="文章标题")
    content: str = Field(..., description="文章内容（支持 Markdown 或纯文本）")
    enable_kb_comparison: bool = Field(default=True, description="是否对比知识库文章")
    enable_web_search: bool = Field(default=True, description="是否进行外部网络搜索")


class AnalyzeContentResponse(BaseModel):
    """Response containing analysis results for content."""
    model_config = {"from_attributes": True}
    quality_score: float
    quality_breakdown: dict[str, float]
    quality_score_details: list[dict[str, Any]]
    comparison_references: list[dict[str, Any]]
    analysis_summary: str
    improvement_suggestions: list[str]
    rubric_version: str
    analysis_duration_ms: int
    hook_type: str
    framework: str
    emotional_triggers: list[str]
    key_phrases: list[str]
    keywords: list[str]
    structure: dict[str, Any]
    style: dict[str, Any]
    target_audience: str
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


@router.post("/analyze-content", response_model=AnalyzeContentResponse)
async def analyze_content(current_user: CurrentUser, body: AnalyzeContentRequest) -> Any:
    """Analyze content without persisting to database.

    This endpoint is designed for evaluating rewritten/imitated articles
    against the same quality standards as入库 articles, without saving
    the article or analysis results.
    """
    from app.core.agents.react_analyzer import ReactAnalyzerAgent
    from app.models import AgentConfig

    # Use the first active analyzer config or fallback defaults
    agent_config = await AgentConfig.find_one(
        AgentConfig.role == "analyzer",
        AgentConfig.is_active == True,  # noqa: E712
    )

    # If no analyzer config, try to find any active config
    if not agent_config:
        agent_config = await AgentConfig.find_one(
            AgentConfig.is_active == True,  # noqa: E712
        )

    # Create a temporary config with user-specified options
    # We modify the config to respect enable_kb_comparison and enable_web_search
    if agent_config and agent_config.analysis_config:
        # Create a copy of analysis_config with user overrides
        analysis_config_dict = agent_config.analysis_config.model_dump()
        analysis_config_dict["enable_kb_comparison"] = body.enable_kb_comparison
        analysis_config_dict["enable_web_search"] = body.enable_web_search

        # Create a temporary config object
        from app.models.agent_config import AnalysisConfig
        temp_analysis_config = AnalysisConfig(**analysis_config_dict)
        agent_config.analysis_config = temp_analysis_config

    agent = ReactAnalyzerAgent(agent_config=agent_config)

    # Prepare content - combine title and content
    full_content = f"# {body.title}\n\n{body.content}"

    # Run analysis
    analysis_data = await agent.run(
        article_content=full_content,
        article_id=None,  # No article_id since we're not persisting
    )

    # Extract and format quality_score_details
    quality_score_details = analysis_data.get("quality_score_details", [])
    formatted_score_details = []
    for detail in quality_score_details:
        if isinstance(detail, dict):
            formatted_score_details.append(detail)
        else:
            formatted_score_details.append(detail.model_dump())

    # Extract and format comparison_references
    comparison_refs = analysis_data.get("comparison_references", [])
    formatted_refs = []
    for ref in comparison_refs:
        if isinstance(ref, dict):
            formatted_refs.append(ref)
        else:
            formatted_refs.append(ref.model_dump())

    # Extract and format trace
    trace = analysis_data.get("trace", [])
    formatted_trace = []
    for step in trace:
        if isinstance(step, dict):
            formatted_trace.append(step)
        else:
            formatted_trace.append(step.model_dump())

    return AnalyzeContentResponse(
        quality_score=analysis_data.get("quality_score", 0.0),
        quality_breakdown=analysis_data.get("quality_breakdown", {}),
        quality_score_details=formatted_score_details,
        comparison_references=formatted_refs,
        analysis_summary=analysis_data.get("analysis_summary", ""),
        improvement_suggestions=analysis_data.get("improvement_suggestions", []),
        rubric_version=analysis_data.get("rubric_version", ""),
        analysis_duration_ms=analysis_data.get("analysis_duration_ms", 0),
        hook_type=analysis_data.get("hook_type", ""),
        framework=analysis_data.get("framework", ""),
        emotional_triggers=analysis_data.get("emotional_triggers", []),
        key_phrases=analysis_data.get("key_phrases", []),
        keywords=analysis_data.get("keywords", []),
        structure=analysis_data.get("structure", {}),
        style=analysis_data.get("style", {}),
        target_audience=analysis_data.get("target_audience", ""),
        trace=formatted_trace,
    )


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
