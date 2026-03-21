"""Unit tests for LocalExecutor."""
import sys
import tempfile
from pathlib import Path

import pytest

from app.core.executors.base import ExecutionResult
from app.core.executors.local import LocalExecutor


@pytest.fixture
def executor() -> LocalExecutor:
    return LocalExecutor()


async def test_normal_execution(executor: LocalExecutor) -> None:
    result = await executor.run(
        command=f"{sys.executable} hello.py",
        scripts={"hello.py": "print('hello world')"},
    )
    assert result.exit_code == 0
    assert "hello world" in result.stdout
    assert result.stderr == ""


async def test_exit_code_nonzero(executor: LocalExecutor) -> None:
    result = await executor.run(
        command=f"{sys.executable} fail.py",
        scripts={"fail.py": "import sys; sys.exit(42)"},
    )
    assert result.exit_code == 42


async def test_timeout(executor: LocalExecutor) -> None:
    result = await executor.run(
        command=f"{sys.executable} sleep.py",
        scripts={"sleep.py": "import time; time.sleep(10)"},
        timeout=1,
    )
    assert result.exit_code == -1
    assert "Timeout" in result.stderr


async def test_tmpdir_cleaned_up(executor: LocalExecutor) -> None:
    original_mkdtemp = tempfile.mkdtemp
    created_dirs: list[str] = []

    def tracking_mkdtemp(**kwargs: object) -> str:
        d = original_mkdtemp(**kwargs)
        created_dirs.append(d)
        return d

    import tempfile as _tmpmod

    original = _tmpmod.mkdtemp
    _tmpmod.mkdtemp = tracking_mkdtemp  # type: ignore[assignment]
    try:
        await executor.run(
            command=f"{sys.executable} ok.py",
            scripts={"ok.py": "print('ok')"},
        )
    finally:
        _tmpmod.mkdtemp = original

    for d in created_dirs:
        assert not Path(d).exists(), f"Temp dir {d} was not cleaned up"


async def test_stdout_truncated(executor: LocalExecutor) -> None:
    # Script that produces more than 32 KB of output
    big_script = "print('x' * 100, end='\\n') \n" * 500
    result = await executor.run(
        command=f"{sys.executable} big.py",
        scripts={"big.py": big_script},
    )
    assert result.exit_code == 0
    # Encoded output must not exceed MAX_OUTPUT_BYTES plus the truncation marker
    assert len(result.stdout.encode()) <= 32 * 1024 + 100
