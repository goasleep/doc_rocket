"""Abstract base for script executors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Result of running a script."""
    stdout: str
    stderr: str
    exit_code: int


class ScriptExecutor(ABC):
    """Abstract interface for running skill scripts."""

    @abstractmethod
    async def run(
        self,
        command: str,
        scripts: dict[str, str],
        working_dir: str | None = None,
        timeout: int = 30,
    ) -> ExecutionResult:
        """Execute a script and return the result.

        Args:
            command: The command to run (e.g., "python script.py").
            scripts: Dict mapping filename -> content of scripts to write to tempdir.
            working_dir: Optional working directory (uses tempdir if None).
            timeout: Timeout in seconds (default 30).
        """
        ...
