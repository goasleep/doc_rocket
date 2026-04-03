"""Insights routes — knowledge base analytics snapshot API."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser
from app.models import (
    InsightSnapshotPublic,
    InsightSnapshotsPublic,
    InsightSnapshotMeta,
    Message,
    RefreshSnapshotResponse,
    TaskRun,
)
from app.services import InsightSnapshotService

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/snapshot/latest", response_model=InsightSnapshotPublic)
async def get_latest_snapshot(current_user: CurrentUser) -> Any:
    """Get the most recent insight snapshot."""
    snapshot = await InsightSnapshotService.get_latest()
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No snapshot found. Please trigger a refresh first.",
        )
    return snapshot


@router.get("/snapshot", response_model=InsightSnapshotsPublic)
async def list_snapshots(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 20,
) -> Any:
    """List snapshot history with metadata only."""
    snapshots, count = await InsightSnapshotService.list_history(skip=skip, limit=limit)

    # Convert to meta format
    meta_list = [
        InsightSnapshotMeta(
            id=s.id,
            scope=s.scope,
            article_count=s.article_count,
            created_at=s.created_at,
        )
        for s in snapshots
    ]

    return InsightSnapshotsPublic(data=meta_list, count=count)


@router.post("/snapshot/refresh", response_model=RefreshSnapshotResponse, status_code=status.HTTP_202_ACCEPTED)
async def refresh_snapshot(current_user: CurrentUser) -> Any:
    """Trigger manual snapshot generation.

    Returns 429 Too Many Requests if a snapshot task is already running.
    """
    # Check for concurrent running task
    running_task = await TaskRun.find_one(
        TaskRun.task_type == "insight_snapshot",
        TaskRun.status == "running",
    )

    if running_task:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A snapshot generation task is already in progress. Please wait for it to complete.",
        )

    # Create TaskRun record
    task_run = TaskRun(
        task_type="insight_snapshot",
        triggered_by="manual",
        status="pending",
    )
    await task_run.insert()

    # Enqueue the task
    from app.tasks.insight_snapshot import generate_insight_snapshot_task
    generate_insight_snapshot_task.delay(str(task_run.id))

    return RefreshSnapshotResponse(
        task_run_id=task_run.id,
        message="Snapshot generation task enqueued successfully.",
    )
