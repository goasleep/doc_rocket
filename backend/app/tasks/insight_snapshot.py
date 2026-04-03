"""Celery task for generating insight snapshots."""
import asyncio
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app, get_worker_loop
from app.models import TaskRun
from app.services import InsightSnapshotService


async def _generate_snapshot_async(task_run_id: str) -> None:
    """Generate insight snapshot and update TaskRun status.

    Args:
        task_run_id: The TaskRun ID to track this execution.
    """
    task_run = await TaskRun.find_one(TaskRun.id == uuid.UUID(task_run_id))
    if not task_run:
        return

    # Mark as running
    task_run.status = "running"
    task_run.started_at = datetime.now(timezone.utc)
    await task_run.save()

    try:
        # Generate the snapshot
        snapshot = await InsightSnapshotService.generate()

        # Mark as done
        task_run.status = "done"
        task_run.ended_at = datetime.now(timezone.utc)
        await task_run.save()

    except Exception as exc:
        # Mark as failed
        task_run.status = "failed"
        task_run.error_message = str(exc)[:500]
        task_run.ended_at = datetime.now(timezone.utc)
        await task_run.save()
        raise


@celery_app.task(name="generate_insight_snapshot_task")
def generate_insight_snapshot_task(task_run_id: str) -> None:
    """Celery task wrapper for generating insight snapshots."""
    get_worker_loop().run_until_complete(_generate_snapshot_async(task_run_id))


async def _generate_snapshot_scheduled_async() -> None:
    """Generate insight snapshot for scheduled execution (redbeat).

    Creates its own TaskRun record with triggered_by="scheduler".
    """
    # Check if there's already a running task
    running_task = await TaskRun.find_one(
        TaskRun.task_type == "insight_snapshot",
        TaskRun.status == "running",
    )

    if running_task:
        # Skip this run if another is in progress
        return

    # Create TaskRun record
    task_run = TaskRun(
        task_type="insight_snapshot",
        triggered_by="scheduler",
        status="pending",
    )
    await task_run.insert()

    # Mark as running
    task_run.status = "running"
    task_run.started_at = datetime.now(timezone.utc)
    await task_run.save()

    try:
        # Generate the snapshot
        snapshot = await InsightSnapshotService.generate()

        # Mark as done
        task_run.status = "done"
        task_run.ended_at = datetime.now(timezone.utc)
        await task_run.save()

    except Exception as exc:
        # Mark as failed
        task_run.status = "failed"
        task_run.error_message = str(exc)[:500]
        task_run.ended_at = datetime.now(timezone.utc)
        await task_run.save()
        raise


@celery_app.task(name="scheduled_insight_snapshot_task")
def scheduled_insight_snapshot_task() -> None:
    """Celery task for scheduled snapshot generation via redbeat."""
    get_worker_loop().run_until_complete(_generate_snapshot_scheduled_async())
