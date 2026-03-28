"""Token usage tracking service for recording and querying LLM consumption."""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
import uuid

from app.models.token_usage import (
    AgentTokenStats,
    ArticleTokenUsage,
    ArticleTokenUsageSummary,
    TokenUsage,
    TokenUsageDaily,
)


class TokenUsageService:
    """Service for recording and querying token usage data."""

    @staticmethod
    async def record_usage(
        agent_config_id: Optional[uuid.UUID],
        agent_config_name: str,
        model_name: str,
        entity_type: str,
        entity_id: Optional[uuid.UUID],
        operation: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        usage_missing: bool = False,
    ) -> TokenUsage:
        """Record a single LLM call's token usage and update daily aggregation.

        Args:
            agent_config_id: UUID of the agent configuration
            agent_config_name: Name of the agent configuration
            model_name: Name of the LLM model used
            entity_type: Type of entity ("article", "workflow", "task", "draft")
            entity_id: UUID of the entity
            operation: Operation performed ("refine", "analyze", "rewrite", "chat")
            prompt_tokens: Number of prompt tokens consumed
            completion_tokens: Number of completion tokens consumed
            total_tokens: Total tokens consumed
            usage_missing: Whether usage data was missing from API response

        Returns:
            The created TokenUsage record
        """
        # Create the usage record
        usage = TokenUsage(
            agent_config_id=agent_config_id,
            agent_config_name=agent_config_name,
            model_name=model_name,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            usage_missing=usage_missing,
        )
        await usage.insert()

        # Update daily aggregation atomically
        await TokenUsageService._update_daily_aggregation(
            agent_config_id=agent_config_id,
            agent_config_name=agent_config_name,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        return usage

    @staticmethod
    async def _update_daily_aggregation(
        agent_config_id: Optional[uuid.UUID],
        agent_config_name: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> None:
        """Update or create the daily aggregation record atomically.

        Uses MongoDB's upsert with $inc for atomic increment operations.
        """
        # Use datetime for the date field (midnight UTC)
        today = datetime.combine(date.today(), datetime.min.time())

        # Try to find existing daily record
        daily = await TokenUsageDaily.find_one(
            TokenUsageDaily.date == today,
            TokenUsageDaily.agent_config_id == agent_config_id,
            TokenUsageDaily.model_name == model_name,
        )

        if daily:
            # Update existing record
            daily.total_prompt_tokens += prompt_tokens
            daily.total_completion_tokens += completion_tokens
            daily.total_tokens += total_tokens
            daily.call_count += 1
            daily.updated_at = datetime.now(timezone.utc)
            await daily.save()
        else:
            # Create new daily record
            daily = TokenUsageDaily(
                date=today,
                agent_config_id=agent_config_id,
                agent_config_name=agent_config_name,
                model_name=model_name,
                total_prompt_tokens=prompt_tokens,
                total_completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                call_count=1,
            )
            await daily.insert()

    @staticmethod
    async def get_agent_daily_stats(
        start_date: date,
        end_date: date,
        agent_config_id: Optional[uuid.UUID] = None,
    ) -> list[AgentTokenStats]:
        """Get aggregated token stats for agents within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            agent_config_id: Optional filter by specific agent

        Returns:
            List of aggregated stats per agent/model combination
        """
        # Convert dates to datetime for MongoDB compatibility
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Build query using Beanie's query API to handle UUID encoding
        query = TokenUsageDaily.find(
            TokenUsageDaily.date >= start_dt,
            TokenUsageDaily.date <= end_dt,
        )

        if agent_config_id:
            query = query.find(TokenUsageDaily.agent_config_id == agent_config_id)

        records = await query.to_list()

        # Aggregate in Python to avoid BSON encoding issues with UUID in pipelines
        stats_map: dict[tuple, dict[str, Any]] = {}
        for r in records:
            key = (r.agent_config_id, r.agent_config_name, r.model_name)
            if key not in stats_map:
                stats_map[key] = {
                    "agent_config_id": r.agent_config_id,
                    "agent_config_name": r.agent_config_name,
                    "model_name": r.model_name,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_tokens": 0,
                    "call_count": 0,
                }
            stats_map[key]["total_prompt_tokens"] += r.total_prompt_tokens
            stats_map[key]["total_completion_tokens"] += r.total_completion_tokens
            stats_map[key]["total_tokens"] += r.total_tokens
            stats_map[key]["call_count"] += r.call_count

        return [AgentTokenStats(**s) for s in stats_map.values()]

    @staticmethod
    async def get_entity_usage(
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> ArticleTokenUsageSummary:
        """Get token usage breakdown for a specific entity.

        Args:
            entity_type: Type of entity ("article", "workflow", "task", "draft")
            entity_id: UUID of the entity

        Returns:
            Summary of all token usage for the entity
        """
        usages = await TokenUsage.find(
            TokenUsage.entity_type == entity_type,
            TokenUsage.entity_id == entity_id,
        ).sort("+created_at").to_list()

        operations = [
            ArticleTokenUsage(
                operation=u.operation,
                model_name=u.model_name,
                prompt_tokens=u.prompt_tokens,
                completion_tokens=u.completion_tokens,
                total_tokens=u.total_tokens,
                created_at=u.created_at,
            )
            for u in usages
        ]

        total_prompt = sum(u.prompt_tokens for u in usages)
        total_completion = sum(u.completion_tokens for u in usages)
        total = sum(u.total_tokens for u in usages)

        return ArticleTokenUsageSummary(
            article_id=entity_id,
            total_tokens=total,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            operation_count=len(usages),
            operations=operations,
        )

    @staticmethod
    async def get_today_stats() -> dict[str, Any]:
        """Get quick stats for today's token consumption.

        Returns:
            Dict with total_tokens, total_calls, and agent breakdown
        """
        today = date.today()
        # Convert to datetime for MongoDB compatibility
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())

        pipeline = [
            {"$match": {"date": {"$gte": start_dt, "$lte": end_dt}}},
            {
                "$group": {
                    "_id": None,
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_calls": {"$sum": "$call_count"},
                    "total_prompt_tokens": {"$sum": "$total_prompt_tokens"},
                    "total_completion_tokens": {"$sum": "$total_completion_tokens"},
                }
            },
        ]

        result = await TokenUsageDaily.aggregate(pipeline).to_list()

        if not result:
            return {
                "total_tokens": 0,
                "total_calls": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "agent_breakdown": [],
            }

        summary = result[0]

        # Get per-agent breakdown
        agent_pipeline = [
            {"$match": {"date": {"$gte": start_dt, "$lte": end_dt}}},
            {
                "$group": {
                    "_id": {
                        "agent_config_id": "$agent_config_id",
                        "agent_config_name": "$agent_config_name",
                    },
                    "total_tokens": {"$sum": "$total_tokens"},
                    "call_count": {"$sum": "$call_count"},
                }
            },
            {"$sort": {"total_tokens": -1}},
        ]

        agent_results = await TokenUsageDaily.aggregate(agent_pipeline).to_list()
        agent_breakdown = [
            {
                "agent_config_id": r["_id"]["agent_config_id"],
                "agent_config_name": r["_id"]["agent_config_name"],
                "total_tokens": r["total_tokens"],
                "call_count": r["call_count"],
            }
            for r in agent_results
        ]

        return {
            "total_tokens": summary.get("total_tokens", 0),
            "total_calls": summary.get("total_calls", 0),
            "total_prompt_tokens": summary.get("total_prompt_tokens", 0),
            "total_completion_tokens": summary.get("total_completion_tokens", 0),
            "agent_breakdown": agent_breakdown,
        }

    @staticmethod
    async def get_yesterday_stats() -> dict[str, Any]:
        """Get quick stats for yesterday's token consumption.

        Returns:
            Dict with total_tokens, total_calls, and agent breakdown
        """
        yesterday = date.today() - timedelta(days=1)
        # Convert to datetime for MongoDB compatibility
        start_dt = datetime.combine(yesterday, datetime.min.time())
        end_dt = datetime.combine(yesterday, datetime.max.time())

        pipeline = [
            {"$match": {"date": {"$gte": start_dt, "$lte": end_dt}}},
            {
                "$group": {
                    "_id": None,
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_calls": {"$sum": "$call_count"},
                    "total_prompt_tokens": {"$sum": "$total_prompt_tokens"},
                    "total_completion_tokens": {"$sum": "$total_completion_tokens"},
                }
            },
        ]

        result = await TokenUsageDaily.aggregate(pipeline).to_list()

        if not result:
            return {
                "total_tokens": 0,
                "total_calls": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "agent_breakdown": [],
            }

        summary = result[0]

        # Get per-agent breakdown
        agent_pipeline = [
            {"$match": {"date": {"$gte": start_dt, "$lte": end_dt}}},
            {
                "$group": {
                    "_id": {
                        "agent_config_id": "$agent_config_id",
                        "agent_config_name": "$agent_config_name",
                    },
                    "total_tokens": {"$sum": "$total_tokens"},
                    "call_count": {"$sum": "$call_count"},
                }
            },
            {"$sort": {"total_tokens": -1}},
        ]

        agent_results = await TokenUsageDaily.aggregate(agent_pipeline).to_list()
        agent_breakdown = [
            {
                "agent_config_id": r["_id"]["agent_config_id"],
                "agent_config_name": r["_id"]["agent_config_name"],
                "total_tokens": r["total_tokens"],
                "call_count": r["call_count"],
            }
            for r in agent_results
        ]

        return {
            "total_tokens": summary.get("total_tokens", 0),
            "total_calls": summary.get("total_calls", 0),
            "total_prompt_tokens": summary.get("total_prompt_tokens", 0),
            "total_completion_tokens": summary.get("total_completion_tokens", 0),
            "agent_breakdown": agent_breakdown,
        }

    @staticmethod
    async def get_trend_data(
        days: int = 30,
        agent_config_id: Optional[uuid.UUID] = None,
    ) -> list[dict[str, Any]]:
        """Get time-series trend data for charting.

        Args:
            days: Number of days to include (default 30)
            agent_config_id: Optional filter by specific agent

        Returns:
            List of daily data points with date, tokens, and calls
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Convert to datetime for MongoDB compatibility
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Build query using Beanie's query API
        query = TokenUsageDaily.find(
            TokenUsageDaily.date >= start_dt,
            TokenUsageDaily.date <= end_dt,
        )

        if agent_config_id:
            query = query.find(TokenUsageDaily.agent_config_id == agent_config_id)

        records = await query.to_list()

        # Aggregate in Python to avoid BSON encoding issues with UUID in pipelines
        date_map: dict[str, dict[str, Any]] = {}
        for r in records:
            date_str = r.date.strftime("%Y-%m-%d") if isinstance(r.date, datetime) else str(r.date)
            if date_str not in date_map:
                date_map[date_str] = {"date": date_str, "total_tokens": 0, "total_calls": 0}
            date_map[date_str]["total_tokens"] += r.total_tokens
            date_map[date_str]["total_calls"] += r.call_count

        # Fill in missing dates with zeros
        filled_results = []

        for i in range(days):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.isoformat()
            if date_str in date_map:
                filled_results.append(date_map[date_str])
            else:
                filled_results.append({
                    "date": date_str,
                    "total_tokens": 0,
                    "total_calls": 0,
                })

        return filled_results
