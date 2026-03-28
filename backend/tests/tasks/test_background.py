"""Tests for Celery background task execution."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.tasks.background import execute_background_command, _run_command_async


class TestExecuteBackgroundCommand:
    """Test cases for execute_background_command Celery task."""

    @pytest.mark.asyncio
    async def test_run_command_async_success(self):
        """Test successful command execution."""
        result = await _run_command_async("echo hello", timeout=10)

        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
        assert result["stderr"] == ""

    @pytest.mark.asyncio
    async def test_run_command_async_timeout(self):
        """Test command timeout handling."""
        with pytest.raises(asyncio.TimeoutError):
            await _run_command_async("sleep 10", timeout=0.1)

    @pytest.mark.asyncio
    async def test_run_command_async_failure(self):
        """Test failed command execution."""
        result = await _run_command_async("exit 1", timeout=10)

        assert result["exit_code"] == 1

    def test_execute_background_command_success(self):
        """Test the Celery task with successful execution."""
        with patch("app.tasks.background.get_worker_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Mock the async result
            mock_loop.run_until_complete.return_value = {
                "exit_code": 0,
                "stdout": "hello world",
                "stderr": "",
            }

            # Create a mock self with request.id
            mock_self = MagicMock()
            mock_self.request.id = "test-task-id"

            result = execute_background_command(
                mock_self,
                command="echo hello",
                timeout=30,
                workflow_run_id="wf-123",
            )

            assert result["task_id"] == "test-task-id"
            assert result["command"] == "echo hello"
            assert result["status"] == "completed"
            assert result["exit_code"] == 0
            assert result["stdout"] == "hello world"
            assert result["workflow_run_id"] == "wf-123"

    def test_execute_background_command_error(self):
        """Test the Celery task with execution error."""
        with patch("app.tasks.background.get_worker_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_until_complete.side_effect = Exception("Command failed")

            mock_self = MagicMock()
            mock_self.request.id = "test-task-id"

            result = execute_background_command(
                mock_self,
                command="invalid_command",
                timeout=30,
            )

            assert result["task_id"] == "test-task-id"
            assert result["status"] == "error"
            assert "Command failed" in result["error"]
