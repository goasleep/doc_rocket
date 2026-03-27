"""Task graph tools for agent task management."""
import json
import uuid
from typing import Any

from app.core.agents.task_graph import TaskGraphManager


async def task_create(
    workflow_run_id: str,
    subject: str,
    description: str = "",
    blocked_by: list[str] | None = None,
    priority: int = 0,
    task_type: str = "general",
) -> str:
    """Create a task in the task graph.

    Args:
        workflow_run_id: The workflow run ID this task belongs to
        subject: Task title/subject
        description: Detailed task description
        blocked_by: List of task IDs this task depends on (optional)
        priority: Task priority, higher = more important (default: 0)
        task_type: Task categorization (default: "general")

    Returns:
        JSON string with created task details
    """
    try:
        wf_id = uuid.UUID(workflow_run_id)
    except ValueError:
        return json.dumps({"error": "Invalid workflow_run_id format"}, ensure_ascii=False)

    # Parse dependency IDs
    dep_ids: list[uuid.UUID] = []
    if blocked_by:
        for dep_id_str in blocked_by:
            try:
                dep_ids.append(uuid.UUID(dep_id_str))
            except ValueError:
                return json.dumps(
                    {"error": f"Invalid blocked_by task ID: {dep_id_str}"},
                    ensure_ascii=False
                )

    manager = TaskGraphManager()
    task = await manager.create_task(
        workflow_run_id=wf_id,
        subject=subject,
        description=description,
        blocked_by=dep_ids or None,
        priority=priority,
        task_type=task_type,
    )

    return json.dumps({
        "id": str(task.id),
        "workflow_run_id": str(task.workflow_run_id),
        "subject": task.subject,
        "description": task.description,
        "status": task.status,
        "blocked_by": [str(tid) for tid in task.blocked_by],
        "priority": task.priority,
        "task_type": task.task_type,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }, ensure_ascii=False)


async def task_update(
    task_id: str,
    subject: str | None = None,
    description: str | None = None,
    add_blocked_by: list[str] | None = None,
    priority: int | None = None,
) -> str:
    """Update a task's properties.

    Args:
        task_id: The task ID to update
        subject: New subject (optional)
        description: New description (optional)
        add_blocked_by: Additional task IDs to add as dependencies (optional)
        priority: New priority value (optional)

    Returns:
        JSON string with updated task details
    """
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return json.dumps({"error": "Invalid task_id format"}, ensure_ascii=False)

    # Parse additional dependency IDs
    dep_ids: list[uuid.UUID] = []
    if add_blocked_by:
        for dep_id_str in add_blocked_by:
            try:
                dep_ids.append(uuid.UUID(dep_id_str))
            except ValueError:
                return json.dumps(
                    {"error": f"Invalid add_blocked_by task ID: {dep_id_str}"},
                    ensure_ascii=False
                )

    manager = TaskGraphManager()
    try:
        task = await manager.update_task(
            task_id=tid,
            subject=subject,
            description=description,
            add_blocked_by=dep_ids or None,
            priority=priority,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    if not task:
        return json.dumps({"error": "Task not found"}, ensure_ascii=False)

    return json.dumps({
        "id": str(task.id),
        "subject": task.subject,
        "description": task.description,
        "status": task.status,
        "blocked_by": [str(tid) for tid in task.blocked_by],
        "priority": task.priority,
    }, ensure_ascii=False)


async def task_claim(
    task_id: str,
    owner: str,
) -> str:
    """Claim a task for execution.

    Args:
        task_id: The task ID to claim
        owner: The agent/role claiming the task

    Returns:
        JSON string with claimed task details or error
    """
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return json.dumps({"error": "Invalid task_id format"}, ensure_ascii=False)

    manager = TaskGraphManager()
    task = await manager.claim_task(task_id=tid, owner=owner)

    if not task:
        return json.dumps({
            "error": "Task not found or not claimable (check dependencies are completed)"
        }, ensure_ascii=False)

    return json.dumps({
        "id": str(task.id),
        "subject": task.subject,
        "status": task.status,
        "owner": task.owner,
        "claimed_at": task.claimed_at.isoformat() if task.claimed_at else None,
    }, ensure_ascii=False)


async def task_complete(
    task_id: str,
    result: str | None = None,
) -> str:
    """Mark a task as completed.

    Args:
        task_id: The task ID to complete
        result: Optional task result/output

    Returns:
        JSON string with completed task details and newly unblocked tasks
    """
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return json.dumps({"error": "Invalid task_id format"}, ensure_ascii=False)

    manager = TaskGraphManager()
    try:
        task, unblocked = await manager.complete_task(task_id=tid, result=result)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    return json.dumps({
        "id": str(task.id),
        "subject": task.subject,
        "status": task.status,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "newly_unblocked_count": len(unblocked),
        "newly_unblocked": [
            {"id": str(t.id), "subject": t.subject} for t in unblocked
        ],
    }, ensure_ascii=False)


async def task_fail(
    task_id: str,
    error: str,
) -> str:
    """Mark a task as failed.

    Args:
        task_id: The task ID to fail
        error: Error message explaining the failure

    Returns:
        JSON string with failed task details
    """
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return json.dumps({"error": "Invalid task_id format"}, ensure_ascii=False)

    manager = TaskGraphManager()
    try:
        task = await manager.fail_task(task_id=tid, error=error)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    return json.dumps({
        "id": str(task.id),
        "subject": task.subject,
        "status": task.status,
        "error_message": task.error_message,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }, ensure_ascii=False)


async def task_list(
    workflow_run_id: str,
    status: str | None = None,
) -> str:
    """List tasks for a workflow run.

    Args:
        workflow_run_id: The workflow run ID to query
        status: Optional status filter (pending, in_progress, completed, failed)

    Returns:
        JSON string with list of tasks
    """
    try:
        wf_id = uuid.UUID(workflow_run_id)
    except ValueError:
        return json.dumps({"error": "Invalid workflow_run_id format"}, ensure_ascii=False)

    manager = TaskGraphManager()
    tasks = await manager.get_tasks_by_status(wf_id, status)

    return json.dumps({
        "count": len(tasks),
        "tasks": [
            {
                "id": str(t.id),
                "subject": t.subject,
                "status": t.status,
                "owner": t.owner,
                "priority": t.priority,
                "blocked_by": [str(tid) for tid in t.blocked_by],
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ],
    }, ensure_ascii=False)


async def task_get_ready(
    workflow_run_id: str,
) -> str:
    """Get all ready tasks (pending with all dependencies completed).

    Args:
        workflow_run_id: The workflow run ID to query

    Returns:
        JSON string with list of ready tasks
    """
    try:
        wf_id = uuid.UUID(workflow_run_id)
    except ValueError:
        return json.dumps({"error": "Invalid workflow_run_id format"}, ensure_ascii=False)

    manager = TaskGraphManager()
    tasks = await manager.get_ready_tasks(wf_id)

    return json.dumps({
        "count": len(tasks),
        "tasks": [
            {
                "id": str(t.id),
                "subject": t.subject,
                "description": t.description,
                "priority": t.priority,
                "task_type": t.task_type,
            }
            for t in tasks
        ],
    }, ensure_ascii=False)


async def task_graph_status(
    workflow_run_id: str,
) -> str:
    """Get overall status of the task graph.

    Args:
        workflow_run_id: The workflow run ID to query

    Returns:
        JSON string with task graph status summary
    """
    try:
        wf_id = uuid.UUID(workflow_run_id)
    except ValueError:
        return json.dumps({"error": "Invalid workflow_run_id format"}, ensure_ascii=False)

    manager = TaskGraphManager()
    status = await manager.get_task_graph_status(wf_id)

    return json.dumps(status, ensure_ascii=False)
