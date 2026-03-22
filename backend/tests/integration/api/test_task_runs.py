"""Integration tests for GET /task-runs API."""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient

from app.models import TaskRun


@pytest.fixture(autouse=True)
async def cleanup_task_runs():
    yield
    await TaskRun.delete_all()


@pytest.mark.anyio
async def test_list_task_runs_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/task-runs/")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_list_task_runs_empty(client: AsyncClient, superuser_token_headers: dict):
    r = await client.get("/api/v1/task-runs/", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["data"] == []


@pytest.mark.anyio
async def test_list_task_runs_sorted_desc(client: AsyncClient, superuser_token_headers: dict):
    """Results should be sorted by created_at DESC."""
    now = datetime.now(timezone.utc)
    older = TaskRun(task_type="analyze", created_at=now - timedelta(hours=1))
    newer = TaskRun(task_type="analyze", created_at=now)
    await older.insert()
    await newer.insert()

    r = await client.get("/api/v1/task-runs/", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 2
    assert datetime.fromisoformat(data[0]["created_at"]) >= datetime.fromisoformat(data[1]["created_at"])


@pytest.mark.anyio
async def test_list_task_runs_count_reflects_total(client: AsyncClient, superuser_token_headers: dict):
    """count field should reflect total matching records, not page size."""
    for _ in range(5):
        await TaskRun(task_type="fetch").insert()

    r = await client.get("/api/v1/task-runs/?limit=2", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 5
    assert len(data["data"]) == 2


@pytest.mark.anyio
async def test_filter_by_task_type_analyze(client: AsyncClient, superuser_token_headers: dict):
    await TaskRun(task_type="analyze").insert()
    await TaskRun(task_type="fetch").insert()
    await TaskRun(task_type="workflow").insert()

    r = await client.get("/api/v1/task-runs/?task_type=analyze", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert all(d["task_type"] == "analyze" for d in data["data"])


@pytest.mark.anyio
async def test_filter_by_task_type_fetch(client: AsyncClient, superuser_token_headers: dict):
    await TaskRun(task_type="analyze").insert()
    await TaskRun(task_type="fetch").insert()

    r = await client.get("/api/v1/task-runs/?task_type=fetch", headers=superuser_token_headers)
    assert r.status_code == 200
    assert all(d["task_type"] == "fetch" for d in r.json()["data"])


@pytest.mark.anyio
async def test_filter_by_status_failed(client: AsyncClient, superuser_token_headers: dict):
    await TaskRun(task_type="analyze", status="done").insert()
    await TaskRun(task_type="analyze", status="failed", error_message="oops").insert()

    r = await client.get("/api/v1/task-runs/?status=failed", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["status"] == "failed"


@pytest.mark.anyio
async def test_filter_by_triggered_by_manual(client: AsyncClient, superuser_token_headers: dict):
    await TaskRun(task_type="analyze", triggered_by="manual").insert()
    await TaskRun(task_type="fetch", triggered_by="scheduler").insert()

    r = await client.get("/api/v1/task-runs/?triggered_by=manual", headers=superuser_token_headers)
    assert r.status_code == 200
    assert all(d["triggered_by"] == "manual" for d in r.json()["data"])


@pytest.mark.anyio
async def test_filter_by_triggered_by_scheduler(client: AsyncClient, superuser_token_headers: dict):
    await TaskRun(task_type="fetch", triggered_by="scheduler").insert()
    await TaskRun(task_type="analyze", triggered_by="manual").insert()

    r = await client.get("/api/v1/task-runs/?triggered_by=scheduler", headers=superuser_token_headers)
    assert r.status_code == 200
    assert all(d["triggered_by"] == "scheduler" for d in r.json()["data"])


@pytest.mark.anyio
async def test_filter_by_triggered_by_agent(client: AsyncClient, superuser_token_headers: dict):
    await TaskRun(task_type="analyze", triggered_by="agent", triggered_by_label="AI").insert()
    await TaskRun(task_type="analyze", triggered_by="manual").insert()

    r = await client.get("/api/v1/task-runs/?triggered_by=agent", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["triggered_by_label"] == "AI"


@pytest.mark.anyio
async def test_filter_by_entity_id(client: AsyncClient, superuser_token_headers: dict):
    target_id = uuid.uuid4()
    await TaskRun(task_type="analyze", entity_id=target_id, entity_type="article").insert()
    await TaskRun(task_type="analyze", entity_id=uuid.uuid4(), entity_type="article").insert()

    r = await client.get(f"/api/v1/task-runs/?entity_id={target_id}", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["entity_id"] == str(target_id)


@pytest.mark.anyio
async def test_filter_by_date_range(client: AsyncClient, superuser_token_headers: dict):
    now = datetime.now(timezone.utc)
    old = TaskRun(task_type="analyze", created_at=now - timedelta(days=10))
    recent = TaskRun(task_type="analyze", created_at=now)
    await old.insert()
    await recent.insert()

    date_from = (now - timedelta(days=1)).isoformat()
    r = await client.get(f"/api/v1/task-runs/?date_from={date_from}", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1


@pytest.mark.anyio
async def test_skip_limit_pagination(client: AsyncClient, superuser_token_headers: dict):
    for i in range(5):
        await TaskRun(task_type="analyze", created_at=datetime.now(timezone.utc) - timedelta(seconds=i)).insert()

    r1 = await client.get("/api/v1/task-runs/?skip=0&limit=2", headers=superuser_token_headers)
    r2 = await client.get("/api/v1/task-runs/?skip=2&limit=2", headers=superuser_token_headers)
    page1_ids = {d["id"] for d in r1.json()["data"]}
    page2_ids = {d["id"] for d in r2.json()["data"]}
    assert len(page1_ids.intersection(page2_ids)) == 0


@pytest.mark.anyio
async def test_get_task_run_by_id(client: AsyncClient, superuser_token_headers: dict):
    run = TaskRun(task_type="analyze", status="done")
    await run.insert()

    r = await client.get(f"/api/v1/task-runs/{run.id}", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(run.id)
    assert data["task_type"] == "analyze"
    assert data["status"] == "done"


@pytest.mark.anyio
async def test_get_task_run_not_found(client: AsyncClient, superuser_token_headers: dict):
    r = await client.get(f"/api/v1/task-runs/{uuid.uuid4()}", headers=superuser_token_headers)
    assert r.status_code == 404
