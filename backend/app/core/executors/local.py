"""LocalExecutor — runs scripts in a temporary directory via subprocess."""
import asyncio
import shlex
import tempfile
from pathlib import Path

from app.core.executors.base import ExecutionResult, ScriptExecutor

MAX_OUTPUT_BYTES = 32 * 1024  # 32 KB


class LocalExecutor(ScriptExecutor):
    """Executes scripts locally in a temp directory."""

    async def run(
        self,
        command: str,
        scripts: dict[str, str],
        working_dir: str | None = None,
        timeout: int = 30,
    ) -> ExecutionResult:
        tmpdir = tempfile.mkdtemp(prefix="skill_")
        try:
            # Write all script files
            for filename, content in scripts.items():
                path = Path(tmpdir) / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            cwd = working_dir or tmpdir
            args = shlex.split(command)

            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                )
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        proc.communicate(), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.communicate()
                    return ExecutionResult(
                        stdout="",
                        stderr=f"Timeout after {timeout}s",
                        exit_code=-1,
                    )

                stdout = stdout_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                stderr = stderr_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                if len(stdout_bytes) > MAX_OUTPUT_BYTES:
                    stdout += "\n[输出已截断]"

                return ExecutionResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=proc.returncode or 0,
                )
            except OSError as e:
                return ExecutionResult(stdout="", stderr=str(e), exit_code=-1)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
