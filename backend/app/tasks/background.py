"""Background task execution using Celery.

Provides async command execution in background workers with result tracking.
"""
import asyncio
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

from app.celery_app import celery_app, get_worker_loop


@celery_app.task(bind=True, max_retries=3)
def execute_background_command(
    self,
    command: str,
    timeout: int = 120,
    workflow_run_id: str | None = None,
) -> dict[str, Any]:
    """Execute a command in a background Celery worker.

    Args:
        command: The shell command to execute
        timeout: Maximum execution time in seconds
        workflow_run_id: Optional workflow run ID for tracking

    Returns:
        Dict with execution results
    """
    task_id = self.request.id
    start_time = datetime.now(timezone.utc)

    try:
        # Run the command using asyncio subprocess
        loop = get_worker_loop()
        result = loop.run_until_complete(
            _run_command_async(command, timeout)
        )

        end_time = datetime.now(timezone.utc)

        return {
            "task_id": task_id,
            "command": command,
            "status": "completed",
            "exit_code": result["exit_code"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "workflow_run_id": workflow_run_id,
        }

    except asyncio.TimeoutError:
        self.retry(countdown=10)
        return {
            "task_id": task_id,
            "command": command,
            "status": "timeout",
            "error": f"Command timed out after {timeout} seconds",
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "command": command,
            "status": "error",
            "error": str(e),
        }


async def _run_command_async(command: str, timeout: int) -> dict[str, Any]:
    """Run a shell command asynchronously.

    Args:
        command: The command to run
        timeout: Timeout in seconds

    Returns:
        Dict with exit_code, stdout, stderr
    """
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )

        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise
