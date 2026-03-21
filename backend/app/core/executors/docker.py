"""DockerExecutor — reserved interface, not yet implemented."""
from app.core.executors.base import ExecutionResult, ScriptExecutor


class DockerExecutor(ScriptExecutor):
    async def run(
        self,
        command: str,
        scripts: dict[str, str],
        working_dir: str | None = None,
        timeout: int = 30,
    ) -> ExecutionResult:
        raise NotImplementedError("DockerExecutor not yet implemented")
