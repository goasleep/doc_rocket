"""TaskRun API routes — unified task execution log."""
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser
from app.models import TaskRun, TaskRunPublic, TaskRunsPublic

router = APIRouter(prefix="/task-runs", tags=["task-runs"])


@router.get("/", response_model=TaskRunsPublic)
async def list_task_runs(
    current_user: CurrentUser,
    task_type: Literal["analyze", "fetch", "workflow"] | None = None,
    status: Literal["pending", "running", "done", "failed"] | None = None,
    triggered_by: Literal["manual", "scheduler", "agent"] | None = None,
    entity_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    filters = []
    if task_type is not None:
        filters.append(TaskRun.task_type == task_type)
    if status is not None:
        filters.append(TaskRun.status == status)
    if triggered_by is not None:
        filters.append(TaskRun.triggered_by == triggered_by)
    if entity_id is not None:
        filters.append(TaskRun.entity_id == entity_id)
    if date_from is not None:
        filters.append(TaskRun.created_at >= date_from)
    if date_to is not None:
        filters.append(TaskRun.created_at <= date_to)

    import asyncio

    if filters:
        query = TaskRun.find(*filters)
    else:
        query = TaskRun.find_all()

    count, data = await asyncio.gather(
        query.count(),
        query.sort("-created_at").skip(skip).limit(limit).to_list(),
    )
    return TaskRunsPublic(data=data, count=count)


@router.get("/{id}", response_model=TaskRunPublic)
async def get_task_run(current_user: CurrentUser, id: uuid.UUID) -> Any:
    task_run = await TaskRun.find_one(TaskRun.id == id)
    if not task_run:
        raise HTTPException(status_code=404, detail="TaskRun not found")
    return task_run
