"""Integration tests for token usage API endpoints."""
import uuid
from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.token_usage import TokenUsage, TokenUsageDaily


@pytest.mark.anyio
class TestTokenUsageAPI:
    """Integration tests for token usage endpoints."""

    async def test_get_today_stats_empty(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test today stats endpoint returns zeros when no data."""
        response = await client.get("/api/v1/token-usage/today", headers=superuser_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_tokens"] == 0
        assert data["total_calls"] == 0
        assert data["agent_breakdown"] == []

    async def test_get_today_stats_with_data(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test today stats endpoint returns correct data."""
        agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())

        # Create daily record
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

        response = await client.get("/api/v1/token-usage/today", headers=superuser_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_tokens"] == 800
        assert data["total_calls"] == 5
        assert data["total_prompt_tokens"] == 500
        assert data["total_completion_tokens"] == 300
        assert len(data["agent_breakdown"]) >= 1

        # Clean up
        await daily.delete()

    async def test_get_yesterday_stats(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test yesterday stats endpoint."""
        agent_id = uuid.uuid4()
        yesterday = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())

        # Create daily record for yesterday
        daily = TokenUsageDaily(
            date=yesterday,
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            total_prompt_tokens=200,
            total_completion_tokens=100,
            total_tokens=300,
            call_count=2,
        )
        await daily.insert()

        response = await client.get("/api/v1/token-usage/yesterday", headers=superuser_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_tokens"] == 300
        assert data["total_calls"] == 2

        # Clean up
        await daily.delete()

    async def test_get_trend_data(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test trend data endpoint."""
        agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())

        # Create daily records
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

        response = await client.get("/api/v1/token-usage/trend?days=7", headers=superuser_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7

        # Verify data points exist
        today_str = date.today().isoformat()
        today_data = next((d for d in data if d["date"] == today_str), None)
        assert today_data is not None
        assert today_data["total_tokens"] == 150

        # Clean up
        await TokenUsageDaily.find(
            TokenUsageDaily.agent_config_id == agent_id
        ).delete()

    async def test_get_trend_data_with_agent_filter(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test trend data endpoint with agent filter."""
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

        response = await client.get(
            f"/api/v1/token-usage/trend?days=7&agent_config_id={agent_id}",
            headers=superuser_token_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7
        total = sum(d["total_tokens"] for d in data)
        assert total == 150  # Only our agent's data

        # Clean up
        await daily1.delete()
        await daily2.delete()

    async def test_get_agent_stats(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test agent stats endpoint."""
        agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())

        # Create daily record
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

        response = await client.get("/api/v1/token-usage/agents", headers=superuser_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our agent
        agent_stats = [s for s in data if s["agent_config_id"] == str(agent_id)]
        assert len(agent_stats) == 1
        assert agent_stats[0]["total_tokens"] == 800
        assert agent_stats[0]["call_count"] == 5

        # Clean up
        await daily.delete()

    async def test_get_agent_stats_with_date_range(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test agent stats endpoint with date range."""
        agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())
        yesterday = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())

        # Create records for different days
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
            date=yesterday,
            agent_config_id=agent_id,
            agent_config_name="TestAgent",
            model_name="gpt-4",
            total_prompt_tokens=200,
            total_completion_tokens=100,
            total_tokens=300,
            call_count=2,
        )
        await daily2.insert()

        start_date = (date.today() - timedelta(days=1)).isoformat()
        end_date = date.today().isoformat()
        response = await client.get(
            f"/api/v1/token-usage/agents?start_date={start_date}&end_date={end_date}",
            headers=superuser_token_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Find our agent
        agent_stats = [s for s in data if s["agent_config_id"] == str(agent_id)]
        assert len(agent_stats) == 1
        assert agent_stats[0]["total_tokens"] == 450  # 150 + 300
        assert agent_stats[0]["call_count"] == 3  # 1 + 2

        # Clean up
        await daily1.delete()
        await daily2.delete()

    async def test_get_single_agent_stats(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test single agent stats endpoint."""
        agent_id = uuid.uuid4()
        today = datetime.combine(date.today(), datetime.min.time())

        # Create daily record
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

        response = await client.get(f"/api/v1/token-usage/agents/{agent_id}", headers=superuser_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["agent_config_id"] == str(agent_id)
        assert data[0]["total_tokens"] == 800

        # Clean up
        await daily.delete()

    async def test_get_article_token_usage(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test article token usage endpoint."""
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
            operation="analyze",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
        )
        await usage2.insert()

        response = await client.get(f"/api/v1/token-usage/articles/{article_id}", headers=superuser_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["article_id"] == str(article_id)
        assert data["total_tokens"] == 450
        assert data["total_prompt_tokens"] == 300
        assert data["total_completion_tokens"] == 150
        assert data["operation_count"] == 2
        assert len(data["operations"]) == 2

        # Clean up
        await usage1.delete()
        await usage2.delete()

    async def test_get_article_token_usage_empty(self, client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
        """Test article token usage endpoint returns empty for unknown article."""
        article_id = uuid.uuid4()

        response = await client.get(f"/api/v1/token-usage/articles/{article_id}", headers=superuser_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["article_id"] == str(article_id)
        assert data["total_tokens"] == 0
        assert data["operation_count"] == 0
        assert data["operations"] == []
