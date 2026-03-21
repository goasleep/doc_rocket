"""Integration tests for the SSE workflow stream endpoint."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.fixtures.content import (  # noqa: F401
    sample_source,
    analyzed_article,
    sample_workflow_run,
    fake_redis_async,
)


@pytest.mark.anyio
async def test_sse_requires_auth(client: AsyncClient, db: None, sample_workflow_run):
    """Without authentication, the SSE endpoint returns 401."""
    import uuid
    r = await client.get(f"/api/v1/workflows/{uuid.uuid4()}/stream")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_sse_delivers_published_events(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    sample_workflow_run,
    fake_redis_async,
):
    """SSE stream delivers events published to the Redis channel in order."""
    run_id = str(sample_workflow_run.id)

    events = [
        json.dumps({"type": "agent_start", "agent": "Writer", "message": "开始处理..."}),
        json.dumps({"type": "agent_output", "agent": "Writer", "content": "初稿完成"}),
        json.dumps({"type": "workflow_paused", "reason": "waiting_human_review"}),
    ]

    # Create a mock async generator that yields the events then stops
    async def mock_event_stream(run_id: str):
        for event in events:
            yield f"data: {event}\n\n"

    with patch("app.api.routes.workflows.workflow_event_stream", side_effect=mock_event_stream):
        async with client.stream(
            "GET",
            f"/api/v1/workflows/{run_id}/stream",
            headers=normal_user_token_headers,
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

            collected = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    collected.append(json.loads(line[6:]))
                if len(collected) >= 3:
                    break

    assert len(collected) == 3
    assert collected[0]["type"] == "agent_start"
    assert collected[1]["type"] == "agent_output"
    assert collected[2]["type"] == "workflow_paused"


@pytest.mark.anyio
async def test_sse_closes_on_workflow_done(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    sample_workflow_run,
):
    """SSE stream closes after receiving a terminal event (workflow_done)."""
    run_id = str(sample_workflow_run.id)

    async def mock_event_stream(run_id: str):
        yield f"data: {json.dumps({'type': 'workflow_done', 'draft_id': 'abc'})}\n\n"

    with patch("app.api.routes.workflows.workflow_event_stream", side_effect=mock_event_stream):
        async with client.stream(
            "GET",
            f"/api/v1/workflows/{run_id}/stream",
            headers=normal_user_token_headers,
        ) as response:
            assert response.status_code == 200
            lines = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    lines.append(line)

    assert len(lines) == 1
    parsed = json.loads(lines[0][6:])
    assert parsed["type"] == "workflow_done"


@pytest.mark.anyio
async def test_sse_sends_keepalive(
    client: AsyncClient,
    normal_user_token_headers: dict,
    db: None,
    sample_workflow_run,
):
    """SSE stream emits keepalive comments when no messages arrive."""
    run_id = str(sample_workflow_run.id)

    async def mock_event_stream(run_id: str):
        yield ": keepalive\n\n"
        yield f"data: {json.dumps({'type': 'workflow_done'})}\n\n"

    with patch("app.api.routes.workflows.workflow_event_stream", side_effect=mock_event_stream):
        async with client.stream(
            "GET",
            f"/api/v1/workflows/{run_id}/stream",
            headers=normal_user_token_headers,
        ) as response:
            assert response.status_code == 200
            raw_lines = []
            async for line in response.aiter_lines():
                raw_lines.append(line)

    keepalive_lines = [l for l in raw_lines if l.startswith(": keepalive")]
    assert len(keepalive_lines) >= 1
