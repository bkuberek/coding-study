"""Opens files in the user's editor: `$VISUAL`, else `$EDITOR` (docs/specs/cli.md#cstudy-start)."""

import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

EDITOR_VARIABLES = ("VISUAL", "EDITOR")
NO_EDITOR = "set $VISUAL or $EDITOR to open the files automatically"


def _run_in_foreground(command: list[str]) -> None:
    """Terminal editors take over the terminal until they exit."""
    subprocess.run(command, check=False)


class EnvEditorOpener:
    def __init__(
        self,
        environ: Mapping[str, str],
        run: Callable[[list[str]], object] = _run_in_foreground,
    ) -> None:
        self._environ = environ
        self._run = run

    def open(self, paths: Sequence[Path]) -> str | None:
        variable = next((name for name in EDITOR_VARIABLES if self._environ.get(name)), None)
        if variable is None:
            return NO_EDITOR
        editor = self._environ[variable]
        try:
            self._run([*shlex.split(editor), *map(str, paths)])
        except OSError as error:
            return f"cannot run ${variable} ({editor}): {error.strerror or error}"
        return None
