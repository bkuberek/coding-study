import subprocess
from collections.abc import Sequence
from pathlib import Path

from coding_study.application.ports import ProbeResult

DEFAULT_TIMEOUT_SECONDS = 30.0
TIMED_OUT_EXIT_CODE = 124
NOT_EXECUTABLE_EXIT_CODE = 126


class SubprocessToolProbe:
    """Runs short version commands; standard output comes before standard error."""

    def __init__(self, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._timeout_seconds = timeout_seconds

    def run(self, command: Sequence[str]) -> ProbeResult | None:
        return _run(command, None, self._timeout_seconds)


class SubprocessCommandRunner:
    """Runs setup commands (`uv sync`, `pnpm install`, Gradle) to completion."""

    def run(self, command: Sequence[str], cwd: Path) -> ProbeResult | None:
        return _run(command, cwd, None)


def _run(
    command: Sequence[str], cwd: Path | None, timeout_seconds: float | None
) -> ProbeResult | None:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return ProbeResult(TIMED_OUT_EXIT_CODE, f"timed out after {timeout_seconds:g}s")
    except OSError as error:
        return ProbeResult(NOT_EXECUTABLE_EXIT_CODE, str(error))
    return ProbeResult(completed.returncode, completed.stdout + completed.stderr)
