"""The IntelliJ open-file launcher (docs/decisions/0010-ide-integration.md).

IntelliJ expands `$FilePath$` only in run configurations that start a JVM, so the open-file
configurations start this tiny jar, which runs `cstudy <args>` and exits with its exit code. The
jar ships inside this package (built by tools/ide-launcher/build.sh); each workspace gets a copy
in its runtime directory, which the run configurations in `.idea/` reference.
"""

from importlib import resources
from pathlib import Path

LAUNCHER_PACKAGE = "coding_study.adapters.ide"
LAUNCHER_NAME = "cstudy-launcher.jar"
LAUNCHER_IN_RUNTIME = f"ide/{LAUNCHER_NAME}"
"""Relative to the workspace's runtime directory."""


def launcher_jar() -> bytes:
    """The jar shipped with this package."""
    return (resources.files(LAUNCHER_PACKAGE) / LAUNCHER_NAME).read_bytes()


class IdeLauncher:
    def __init__(self, runtime: Path) -> None:
        """`runtime` is the workspace's runtime directory."""
        self._path = runtime / LAUNCHER_IN_RUNTIME

    @property
    def path(self) -> Path:
        return self._path

    def is_current(self) -> bool:
        return self._path.is_file() and self._path.read_bytes() == launcher_jar()

    def install(self) -> None:
        """Copies the shipped jar unless an identical copy is there, which keeps its timestamp."""
        if self.is_current():
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_bytes(launcher_jar())
