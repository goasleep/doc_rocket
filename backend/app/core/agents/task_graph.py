"""Task graph manager for DAG-based task dependency management."""
import uuid
from datetime import datetime, timezone
from typing import Any

from beanie.operators import In

from app.models.task_graph import TaskNode


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class TaskGraphManager:
    """Manages task dependency graph operations.

    Provides operations for creating tasks, managing dependencies,
    claiming tasks for execution, and completing tasks with auto-unblocking.
    """

    async def create_task(
        self,
        workflow_run_id: uuid.UUID,
        subject: str,
        description: str = "",
        blocked_by: list[uuid.UUID] | None = None,
        priority: int = 0,
        task_type: str = "general",
    ) -> TaskNode:
        """Create a new task with optional dependencies.

        Args:
            workflow_run_id: The workflow run this task belongs to
            subject: Task title/subject
            description: Detailed task description
            blocked_by: List of task IDs this task depends on
            priority: Task priority (higher = more important)
            task_type: Task categorization

        Returns:
            The created TaskNode
        """
        task = TaskNode(
            workflow_run_id=workflow_run_id,
            subject=subject,
            description=description,
            blocked_by=blocked_by or [],
            priority=priority,
            task_type=task_type,
            status="pending",
        )
        await task.insert()

        # Update blocks relationships on dependency tasks
        if blocked_by:
            deps = await TaskNode.find(In(TaskNode.id, blocked_by)).to_list()
            for dep_task in deps:
                if task.id not in dep_task.blocks:
                    dep_task.blocks.append(task.id)
                    await dep_task.save()

        return task

    async def claim_task(
        self,
        task_id: uuid.UUID,
        owner: str,
    ) -> TaskNode | None:
        """Claim a task for execution atomically.

        Args:
            task_id: The task ID to claim
            owner: The agent/role claiming the task

        Returns:
            The claimed TaskNode, or None if task not found or not claimable
        """
        task = await TaskNode.find_one(TaskNode.id == task_id)
        if not task:
            return None

        # Non-pending tasks cannot be claimed early-exit without lock
        if task.status != "pending":
            return None

        # Verify all dependencies are completed before competing for the task
        if task.blocked_by:
            deps = await TaskNode.find(In(TaskNode.id, task.blocked_by)).to_list()
            dep_map = {dep.id: dep for dep in deps}
            for dep_id in task.blocked_by:
                dep_task = dep_map.get(dep_id)
                if not dep_task or dep_task.status != "completed":
                    return None

        now = get_datetime_utc()
        # Atomically update from pending -> in_progress only if still pending
        update_result = await TaskNode.find_one(
            TaskNode.id == task_id,
            TaskNode.status == "pending",
        ).update({
            "$set": {
                "status": "in_progress",
                "owner": owner,
                "claimed_at": now,
            }
        })

        # Beanie update returns the number of matched documents in some versions,
        # but the API can vary. Safely check whether anything was modified.
        modified_count = getattr(update_result, "modified_count", None)
        if modified_count is None:
            # Fallback: check raw result dict / pymongo write result
            raw = getattr(update_result, "raw_result", None) or update_result
            if isinstance(raw, dict):
                modified_count = raw.get("nModified") or raw.get("modifiedCount")
        if not modified_count:
            return None

        # Refresh the document to reflect the update
        task = await TaskNode.find_one(TaskNode.id == task_id)
        return task

    async def complete_task(
        self,
        task_id: uuid.UUID,
        result: str | None = None,
    ) -> tuple[TaskNode, list[TaskNode]]:
        """Mark task as completed and return newly unblocked tasks.

        Args:
            task_id: The task ID to complete
            result: Optional task result/output

        Returns:
            Tuple of (completed task, list of newly unblocked tasks)
        """
        task = await TaskNode.find_one(TaskNode.id == task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.mark_completed(result)
        await task.save()

        # Find newly unblocked tasks
        unblocked: list[TaskNode] = []
        if task.blocks:
            blocked_tasks = await TaskNode.find(In(TaskNode.id, task.blocks)).to_list()
            # Batch load all dependencies for pending blocked tasks
            dep_ids: set[uuid.UUID] = set()
            for bt in blocked_tasks:
                if bt.status == "pending":
                    dep_ids.update(bt.blocked_by)
            if dep_ids:
                all_deps = await TaskNode.find(In(TaskNode.id, list(dep_ids))).to_list()
                dep_map = {dep.id: dep for dep in all_deps}
            else:
                dep_map = {}

            for blocked_task in blocked_tasks:
                if blocked_task.status == "pending":
                    all_deps_completed = True
                    for dep_id in blocked_task.blocked_by:
                        dep_task = dep_map.get(dep_id)
                        if not dep_task or dep_task.status != "completed":
                            all_deps_completed = False
                            break

                    if all_deps_completed:
                        unblocked.append(blocked_task)

        return task, unblocked

    async def fail_task(
        self,
        task_id: uuid.UUID,
        error: str,
    ) -> TaskNode:
        """Mark task as failed.

        Args:
            task_id: The task ID to fail
            error: Error message

        Returns:
            The failed TaskNode
        """
        task = await TaskNode.find_one(TaskNode.id == task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.mark_failed(error)
        await task.save()
        return task

    async def get_ready_tasks(
        self,
        workflow_run_id: uuid.UUID,
    ) -> list[TaskNode]:
        """Get all pending tasks with no blockers (all dependencies completed).

        Args:
            workflow_run_id: The workflow run to query

        Returns:
            List of ready TaskNode objects
        """
        # Get all pending tasks for this workflow
        pending_tasks = await TaskNode.find(
            TaskNode.workflow_run_id == workflow_run_id,
            TaskNode.status == "pending",
        ).to_list()

        ready: list[TaskNode] = []
        if pending_tasks:
            dep_ids: set[uuid.UUID] = set()
            for task in pending_tasks:
                dep_ids.update(task.blocked_by)
            if dep_ids:
                all_deps = await TaskNode.find(In(TaskNode.id, list(dep_ids))).to_list()
                dep_map = {dep.id: dep for dep in all_deps}
            else:
                dep_map = {}

            for task in pending_tasks:
                all_deps_completed = True
                for dep_id in task.blocked_by:
                    dep_task = dep_map.get(dep_id)
                    if not dep_task or dep_task.status != "completed":
                        all_deps_completed = False
                        break

                if all_deps_completed:
                    ready.append(task)

        # Sort by priority (descending)
        ready.sort(key=lambda t: t.priority, reverse=True)
        return ready

    async def get_tasks_by_status(
        self,
        workflow_run_id: uuid.UUID,
        status: str | None = None,
    ) -> list[TaskNode]:
        """Get tasks filtered by status.

        Args:
            workflow_run_id: The workflow run to query
            status: Optional status filter (pending, in_progress, completed, failed)

        Returns:
            List of matching TaskNode objects
        """
        query = TaskNode.workflow_run_id == workflow_run_id
        if status:
            query = query & (TaskNode.status == status)

        return await TaskNode.find(query).to_list()

    async def update_task(
        self,
        task_id: uuid.UUID,
        subject: str | None = None,
        description: str | None = None,
        add_blocked_by: list[uuid.UUID] | None = None,
        priority: int | None = None,
    ) -> TaskNode | None:
        """Update task properties.

        Args:
            task_id: The task ID to update
            subject: New subject (optional)
            description: New description (optional)
            add_blocked_by: Additional dependencies to add (optional)
            priority: New priority (optional)

        Returns:
            Updated TaskNode, or None if not found
        """
        task = await TaskNode.find_one(TaskNode.id == task_id)
        if not task:
            return None

        if subject is not None:
            task.subject = subject
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority

        if add_blocked_by:
            # Batch fetch dependency tasks
            new_dep_ids = [dep_id for dep_id in add_blocked_by if dep_id not in task.blocked_by]
            if new_dep_ids:
                dep_tasks = await TaskNode.find(In(TaskNode.id, new_dep_ids)).to_list()
                dep_map = {dep.id: dep for dep in dep_tasks}
                for dep_id in new_dep_ids:
                    if await self._would_create_cycle(task.id, dep_id):
                        raise ValueError(f"Adding dependency {dep_id} would create a cycle")
                    task.blocked_by.append(dep_id)

                    dep_task = dep_map.get(dep_id)
                    if dep_task and task.id not in dep_task.blocks:
                        dep_task.blocks.append(task.id)
                        await dep_task.save()

        await task.save()
        return task

    async def _would_create_cycle(
        self,
        task_id: uuid.UUID,
        new_dependency_id: uuid.UUID,
    ) -> bool:
        """Check if adding new_dependency_id as a dependency would create a cycle.

        Args:
            task_id: The task that would get the new dependency
            new_dependency_id: The proposed new dependency

        Returns:
            True if this would create a cycle
        """
        # If the new dependency depends (directly or indirectly) on task_id, it's a cycle
        visited: set[uuid.UUID] = set()
        to_visit = [new_dependency_id]

        while to_visit:
            # Batch load next frontier
            fetch_ids = [tid for tid in to_visit if tid not in visited]
            if not fetch_ids:
                break
            tasks = await TaskNode.find(In(TaskNode.id, fetch_ids)).to_list()
            task_map = {t.id: t for t in tasks}

            to_visit = []
            for tid in fetch_ids:
                if tid in visited:
                    continue
                if tid == task_id:
                    return True
                visited.add(tid)
                current_task = task_map.get(tid)
                if current_task:
                    to_visit.extend(current_task.blocked_by)

        return False

    async def detect_cycles(
        self,
        workflow_run_id: uuid.UUID,
    ) -> list[list[uuid.UUID]]:
        """Detect all cycles in the task graph.

        Args:
            workflow_run_id: The workflow run to check

        Returns:
            List of cycles, where each cycle is a list of task IDs
        """
        tasks = await TaskNode.find(
            TaskNode.workflow_run_id == workflow_run_id
        ).to_list()

        task_ids = {t.id for t in tasks}
        adjacency = {t.id: t.blocks for t in tasks}

        cycles: list[list[uuid.UUID]] = []
        visited: set[uuid.UUID] = set()
        rec_stack: set[uuid.UUID] = set()
        path: list[uuid.UUID] = []

        def dfs(node_id: uuid.UUID) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                if neighbor not in task_ids:
                    continue
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node_id)

        for task_id in task_ids:
            if task_id not in visited:
                dfs(task_id)

        return cycles

    async def get_task_graph_status(
        self,
        workflow_run_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get overall status of the task graph.

        Args:
            workflow_run_id: The workflow run to query

        Returns:
            Dict with status summary
        """
        all_tasks = await TaskNode.find(
            TaskNode.workflow_run_id == workflow_run_id
        ).to_list()

        status_counts: dict[str, int] = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
        }

        for task in all_tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1

        ready_tasks = await self.get_ready_tasks(workflow_run_id)
        cycles = await self.detect_cycles(workflow_run_id)

        return {
            "total_tasks": len(all_tasks),
            "status_counts": status_counts,
            "ready_tasks": len(ready_tasks),
            "ready_task_ids": [str(t.id) for t in ready_tasks],
            "has_cycles": len(cycles) > 0,
            "cycles": [[str(tid) for tid in cycle] for cycle in cycles],
            "is_complete": status_counts["pending"] == 0 and status_counts["in_progress"] == 0,
        }
