"""Unit tests for TokenUsageService."""
import uuid
from datetime import date, datetime, timedelta

import pytest

from app.models.token_usage import (
    AgentTokenStats,
    TokenUsage,
    TokenUsageDaily,
)
from app.services.token_usage import TokenUsageService


@pytest.mark.anyio
class TestTokenUsageService:
    """Tests for TokenUsageService."""

    async def test_record_usage_creates_token_usage(self, db):
        """Verify record_usage creates a TokenUsage record."""
        agent_id = uuid.uuid4()
        article_id = uuid.uuid4()

        usage = await TokenUsageService.record_usage(
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            entity_type="article",
            entity_id=article_id,
            operation="refine",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        assert usage.agent_config_id == agent_id
        assert usage.agent_config_name == "TestAgent"
        assert usage.model_name == "gpt-4"
        assert usage.entity_type == "article"
        assert usage.entity_id == article_id
        assert usage.operation == "refine"
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.usage_missing is False

        # Clean up
        await usage.delete()

    async def test_record_usage_creates_daily_aggregation(self, db):
        """Verify record_usage creates or updates TokenUsageDaily."""
        agent_id = uuid.uuid4()
        article_id = uuid.uuid4()

        await TokenUsageService.record_usage(
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            entity_type="article",
            entity_id=article_id,
            operation="refine",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        # Check daily aggregation was created
        daily = await TokenUsageDaily.find_one(
            TokenUsageDaily.agent_config_id == agent_id,
            TokenUsageDaily.model_name == "gpt-4",
        )

        assert daily is not None
        assert daily.total_prompt_tokens == 100
        assert daily.total_completion_tokens == 50
        assert daily.total_tokens == 150
        assert daily.call_count == 1

        # Clean up
        await daily.delete()
        usage = await TokenUsage.find_one(TokenUsage.agent_config_id == agent_id)
        if usage:
            await usage.delete()

    async def test_record_usage_updates_existing_daily(self, db):
        """Verify multiple usages are aggregated in daily record."""
        agent_id = uuid.uuid4()

        # Record first usage
        await TokenUsageService.record_usage(
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            entity_type="article",
            entity_id=uuid.uuid4(),
            operation="refine",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        # Record second usage
        await TokenUsageService.record_usage(
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            entity_type="article",
            entity_id=uuid.uuid4(),
            operation="analyze",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
        )

        # Check aggregation
        daily = await TokenUsageDaily.find_one(
            TokenUsageDaily.agent_config_id == agent_id,
            TokenUsageDaily.model_name == "gpt-4",
        )

        assert daily is not None
        assert daily.total_prompt_tokens == 300  # 100 + 200
        assert daily.total_completion_tokens == 150  # 50 + 100
        assert daily.total_tokens == 450  # 150 + 300
        assert daily.call_count == 2

        # Clean up
        await daily.delete()
        await TokenUsage.find(TokenUsage.agent_config_id == agent_id).delete()

    async def test_record_usage_with_missing_usage_flag(self, db):
        """Verify usage_missing flag is recorded correctly."""
        usage = await TokenUsageService.record_usage(
            agent_config_id=uuid.uuid4(),
            agent_config_name="TestAgent",
            model_name="gpt-4",
            entity_type="article",
            entity_id=uuid.uuid4(),
            operation="refine",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            usage_missing=True,
        )

        assert usage.usage_missing is True

        # Clean up
        await usage.delete()

    async def test_get_agent_daily_stats(self, db):
        """Verify agent daily stats aggregation."""
        agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())

        # Create daily records
        daily1 = TokenUsageDaily(
            date=today,
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            total_prompt_tokens=100,
            total_completion_tokens=50,
            total_tokens=150,
            call_count=1,
        )
        await daily1.insert()

        daily2 = TokenUsageDaily(
            date=today - timedelta(days=1),
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            total_prompt_tokens=200,
            total_completion_tokens=100,
            total_tokens=300,
            call_count=2,
        )
        await daily2.insert()

        # Get stats for last 2 days
        stats = await TokenUsageService.get_agent_daily_stats(
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
        )

        assert len(stats) >= 1
        # Find our agent in results
        agent_stats = [s for s in stats if s.agent_config_id == agent_id]
        assert len(agent_stats) == 1
        assert agent_stats[0].total_tokens == 450  # 150 + 300
        assert agent_stats[0].call_count == 3  # 1 + 2

        # Clean up
        await daily1.delete()
        await daily2.delete()

    async def test_get_entity_usage(self, db):
        """Verify entity usage breakdown."""
        article_id = uuid.uuid4()

        # Create usage records
        usage1 = TokenUsage(
            agent_config_id=uuid.uuid4(),
            agent_config_name="Writer",
            model_name="gpt-4",
            entity_type="article",
            entity_id=article_id,
            operation="refine",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        await usage1.insert()

        usage2 = TokenUsage(
            agent_config_id=uuid.uuid4(),
            agent_config_name="Editor",
            model_name="gpt-4",
            entity_type="article",
            entity_id=article_id,
            operation="rewrite",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
        )
        await usage2.insert()

        # Get entity usage
        summary = await TokenUsageService.get_entity_usage("article", article_id)

        assert summary.article_id == article_id
        assert summary.total_tokens == 450
        assert summary.total_prompt_tokens == 300
        assert summary.total_completion_tokens == 150
        assert summary.operation_count == 2
        assert len(summary.operations) == 2

        # Clean up
        await usage1.delete()
        await usage2.delete()

    async def test_get_today_stats(self, db):
        """Verify today stats returns correct aggregation."""
        # Clean up any existing data first
        await TokenUsageDaily.delete_all()

        agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())

        # Create today's daily record
        daily = TokenUsageDaily(
            date=today,
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            total_prompt_tokens=500,
            total_completion_tokens=300,
            total_tokens=800,
            call_count=5,
        )
        await daily.insert()

        stats = await TokenUsageService.get_today_stats()

        assert stats["total_tokens"] == 800
        assert stats["total_calls"] == 5
        assert stats["total_prompt_tokens"] == 500
        assert stats["total_completion_tokens"] == 300
        assert len(stats["agent_breakdown"]) >= 1

        # Clean up
        await daily.delete()

    async def test_get_yesterday_stats_empty(self, db):
        """Verify yesterday stats returns zeros when no data."""
        stats = await TokenUsageService.get_yesterday_stats()

        assert stats["total_tokens"] == 0
        assert stats["total_calls"] == 0
        assert stats["agent_breakdown"] == []

    async def test_get_trend_data(self, db):
        """Verify trend data returns time series."""
        # Clean up any existing data first
        await TokenUsageDaily.delete_all()

        agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())

        # Create daily records for last 3 days
        for i in range(3):
            daily = TokenUsageDaily(
                date=today - timedelta(days=i),
                agent_config_id=agent_id,
                agent_config_name="TestAgent",
                model_name="gpt-4",
                total_prompt_tokens=100 * (i + 1),
                total_completion_tokens=50 * (i + 1),
                total_tokens=150 * (i + 1),
                call_count=i + 1,
            )
            await daily.insert()

        # Get 7-day trend
        trend = await TokenUsageService.get_trend_data(days=7)

        assert len(trend) == 7
        # Last 3 days should have data (check by string date)
        today_str = date.today().isoformat()
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        day2_str = (date.today() - timedelta(days=2)).isoformat()

        today_data = next((d for d in trend if d["date"] == today_str), None)
        yesterday_data = next((d for d in trend if d["date"] == yesterday_str), None)
        day2_data = next((d for d in trend if d["date"] == day2_str), None)

        assert today_data is not None
        assert today_data["total_tokens"] == 150
        assert yesterday_data is not None
        assert yesterday_data["total_tokens"] == 300
        assert day2_data is not None
        assert day2_data["total_tokens"] == 450

        # Clean up
        await TokenUsageDaily.find(
            TokenUsageDaily.agent_config_id == agent_id
        ).delete()

    async def test_get_trend_data_with_agent_filter(self, db):
        """Verify trend data can be filtered by agent."""
        # Clean up any existing data first
        await TokenUsageDaily.delete_all()

        agent_id = uuid.uuid4()
        other_agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())

        # Create records for different agents
        daily1 = TokenUsageDaily(
            date=today,
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            total_prompt_tokens=100,
            total_completion_tokens=50,
            total_tokens=150,
            call_count=1,
        )
        await daily1.insert()

        daily2 = TokenUsageDaily(
            date=today,
            agent_config_id=other_agent_id,
            agent_config_name="OtherAgent",
            model_name="gpt-4",
            total_prompt_tokens=500,
            total_completion_tokens=300,
            total_tokens=800,
            call_count=5,
        )
        await daily2.insert()

        # Get trend for specific agent
        trend = await TokenUsageService.get_trend_data(days=7, agent_config_id=agent_id)

        assert len(trend) == 7
        # Should only include our agent's data
        total = sum(d["total_tokens"] for d in trend)
        assert total == 150

        # Clean up
        await daily1.delete()
        await daily2.delete()
