"""Running the committed Gradle wrapper and reading its compiler output (ADR 0003)."""

import os
import re
import subprocess
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_study.domain.errors import RunnerStartError

WRAPPER = "gradlew"
WRAPPER_PROPERTIES = "gradle/wrapper/gradle-wrapper.properties"
MAX_DIAGNOSTIC_LINES = 40
OUTPUT_TAIL_LINES = 20
_DISTRIBUTION_VERSION = re.compile(r"gradle-([0-9][^-/]*(?:-[a-z]+[0-9-]*)?)-(?:bin|all)\.zip")
_DAEMON_LOG = re.compile(r"daemon-(\d+)\.out\.log")


@dataclass(frozen=True, slots=True)
class GradleOutcome:
    exit_code: int
    output: str
    """Standard output and standard error, interleaved as Gradle wrote them."""


class GradleBuild(Protocol):
    """The Gradle operations the JVM runner needs; tests substitute a fake."""

    def daemon_running(self) -> bool: ...

    def run(self, arguments: Sequence[str]) -> GradleOutcome:
        """Raises RunnerStartError when Gradle cannot be started at all."""
        ...


class DaemonRegistry:
    """Whether a Gradle daemon of one version is alive, from its log files.

    Each daemon writes `<gradle user home>/daemon/<version>/daemon-<pid>.out.log`; a live pid
    means the next build skips the daemon's start-up. It only decides whether to print a notice.
    """

    def __init__(self, gradle_user_home: Path, version: str) -> None:
        self._directory = gradle_user_home / "daemon" / version

    def daemon_running(self) -> bool:
        if not self._directory.is_dir():
            return False
        pids = (_DAEMON_LOG.fullmatch(path.name) for path in self._directory.iterdir())
        return any(_is_alive(int(match.group(1))) for match in pids if match)


class WrapperGradle:
    """`GradleBuild` backed by the workspace's `jvm/gradlew`, run from that project."""

    def __init__(self, workspace: Path, gradle_user_home: Path) -> None:
        self._workspace = workspace
        self._gradle_user_home = gradle_user_home

    def daemon_running(self) -> bool:
        version = wrapper_gradle_version(self._workspace / WRAPPER_PROPERTIES)
        return (
            version is not None and DaemonRegistry(self._gradle_user_home, version).daemon_running()
        )

    def run(self, arguments: Sequence[str]) -> GradleOutcome:
        wrapper = self._workspace / WRAPPER
        if not wrapper.is_file():
            raise RunnerStartError(
                f"{wrapper} is missing; run `cstudy doctor` to set up the JVM workspace"
            )
        try:
            completed = subprocess.run(
                [str(wrapper), *arguments],
                cwd=self._workspace,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
        except OSError as error:
            raise RunnerStartError(f"cannot run {wrapper}: {error.strerror or error}") from error
        return GradleOutcome(
            completed.returncode, completed.stdout.decode("utf-8", errors="replace")
        )


def default_gradle_user_home() -> Path:
    configured = os.environ.get("GRADLE_USER_HOME")
    return Path(configured) if configured else Path.home() / ".gradle"


def wrapper_gradle_version(properties: Path) -> str | None:
    """The Gradle version in the wrapper's `distributionUrl`, or None when unreadable."""
    try:
        text = properties.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _DISTRIBUTION_VERSION.search(text)
    return match.group(1) if match else None


def compiler_diagnostics(output: str, source_directory: str) -> tuple[str, ...]:
    """Compiler lines that mention `source_directory`, each followed by its indented context
    (javac's source excerpt, caret and symbol lines), at most MAX_DIAGNOSTIC_LINES."""
    kept: list[str] = []
    in_diagnostic = False
    for line in output.splitlines():
        if source_directory in line:
            in_diagnostic = True
        elif not (in_diagnostic and line[:1].isspace() and line.strip()):
            in_diagnostic = False
        if in_diagnostic:
            kept.append(line)
    return tuple(kept[:MAX_DIAGNOSTIC_LINES])


def output_tail(output: str) -> tuple[str, ...]:
    return tuple(deque(output.splitlines(), maxlen=OUTPUT_TAIL_LINES))


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
