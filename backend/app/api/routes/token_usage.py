"""Token usage tracking API routes."""
import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.api.deps import CurrentUser
from app.services.token_usage import TokenUsageService

router = APIRouter(prefix="/token-usage", tags=["token-usage"])


class AgentBreakdownItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_config_id: uuid.UUID | None
    agent_config_name: str
    total_tokens: int
    call_count: int


class TodayStatsResponse(BaseModel):
    total_tokens: int
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    agent_breakdown: list[AgentBreakdownItem]


class YesterdayStatsResponse(BaseModel):
    total_tokens: int
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    agent_breakdown: list[AgentBreakdownItem]


class TrendDataPoint(BaseModel):
    date: str
    total_tokens: int
    total_calls: int


class AgentStatsResponse(BaseModel):
    agent_config_id: uuid.UUID | None
    agent_config_name: str
    model_name: str
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    call_count: int


class ArticleTokenUsage(BaseModel):
    operation: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: str


class ArticleTokenUsageSummary(BaseModel):
    article_id: uuid.UUID
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    operation_count: int
    operations: list[ArticleTokenUsage]


@router.get("/today", response_model=TodayStatsResponse)
async def get_today_stats(
    current_user: CurrentUser,
) -> Any:
    """Get today's token usage statistics."""
    stats = await TokenUsageService.get_today_stats()
    return TodayStatsResponse(**stats)


@router.get("/yesterday", response_model=YesterdayStatsResponse)
async def get_yesterday_stats(
    current_user: CurrentUser,
) -> Any:
    """Get yesterday's token usage statistics."""
    stats = await TokenUsageService.get_yesterday_stats()
    return YesterdayStatsResponse(**stats)


@router.get("/trend", response_model=list[TrendDataPoint])
async def get_trend_data(
    current_user: CurrentUser,
    days: int = Query(default=7, ge=1, le=90),
    agent_config_id: uuid.UUID | None = None,
) -> Any:
    """Get time-series trend data for token usage.

    Args:
        days: Number of days to include (1-90, default 7)
        agent_config_id: Optional filter by specific agent
    """
    trend = await TokenUsageService.get_trend_data(
        days=days,
        agent_config_id=agent_config_id,
    )
    return [TrendDataPoint(**item) for item in trend]


@router.get("/agents", response_model=list[AgentStatsResponse])
async def get_agent_stats(
    current_user: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
    agent_config_id: uuid.UUID | None = None,
) -> Any:
    """Get aggregated token stats for agents within a date range.

    Args:
        start_date: Start date (inclusive), defaults to 7 days ago
        end_date: End date (inclusive), defaults to today
        agent_config_id: Optional filter by specific agent
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=6)

    stats = await TokenUsageService.get_agent_daily_stats(
        start_date=start_date,
        end_date=end_date,
        agent_config_id=agent_config_id,
    )

    return [
        AgentStatsResponse(
            agent_config_id=s.agent_config_id,
            agent_config_name=s.agent_config_name,
            model_name=s.model_name,
            total_prompt_tokens=s.total_prompt_tokens,
            total_completion_tokens=s.total_completion_tokens,
            total_tokens=s.total_tokens,
            call_count=s.call_count,
        )
        for s in stats
    ]


@router.get("/agents/{agent_id}", response_model=list[AgentStatsResponse])
async def get_single_agent_stats(
    current_user: CurrentUser,
    agent_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Any:
    """Get token stats for a specific agent.

    Args:
        agent_id: UUID of the agent configuration
        start_date: Start date (inclusive), defaults to 7 days ago
        end_date: End date (inclusive), defaults to today
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=6)

    stats = await TokenUsageService.get_agent_daily_stats(
        start_date=start_date,
        end_date=end_date,
        agent_config_id=agent_id,
    )

    return [
        AgentStatsResponse(
            agent_config_id=s.agent_config_id,
            agent_config_name=s.agent_config_name,
            model_name=s.model_name,
            total_prompt_tokens=s.total_prompt_tokens,
            total_completion_tokens=s.total_completion_tokens,
            total_tokens=s.total_tokens,
            call_count=s.call_count,
        )
        for s in stats
    ]


@router.get("/articles/{article_id}", response_model=ArticleTokenUsageSummary)
async def get_article_token_usage(
    current_user: CurrentUser,
    article_id: uuid.UUID,
) -> Any:
    """Get token usage breakdown for a specific article."""
    summary = await TokenUsageService.get_entity_usage(
        entity_type="article",
        entity_id=article_id,
    )

    return ArticleTokenUsageSummary(
        article_id=summary.article_id,
        total_tokens=summary.total_tokens,
        total_prompt_tokens=summary.total_prompt_tokens,
        total_completion_tokens=summary.total_completion_tokens,
        operation_count=summary.operation_count,
        operations=[
            ArticleTokenUsage(
                operation=op.operation,
                model_name=op.model_name,
                prompt_tokens=op.prompt_tokens,
                completion_tokens=op.completion_tokens,
                total_tokens=op.total_tokens,
                created_at=op.created_at.isoformat(),
            )
            for op in summary.operations
        ],
    )
