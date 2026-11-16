"""Whether the program of each language is there (docs/specs/cli.md#cstudy-verify).

`node`, `go` and `cargo` are looked up on `PATH` as the runners start them; Python runs from the
workspace's own interpreter. Java and Kotlin are the selected JDK's, not this check's.
"""

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from coding_study.domain.layout import PYTHON_INTERPRETER, PYTHON_PROJECT
from coding_study.domain.problem import Language

PATH_PROGRAMS: Mapping[Language, str | None] = {
    Language.PYTHON: None,
    Language.TYPESCRIPT: "node",
    Language.JAVA: None,
    Language.KOTLIN: None,
    Language.GO: "go",
    Language.RUST: "cargo",
}
"""The program each language needs on `PATH`; None: Python has the workspace's interpreter, and Java
and Kotlin the selected JDK."""
SYNC_FIX = "cstudy doctor --fix"


class PathToolchainCheck:
    def __init__(self, environ: Mapping[str, str], workspace: Path) -> None:
        self._environ = environ
        self._workspace = workspace

    def missing(self, language: Language) -> str | None:
        if language is Language.PYTHON:
            return self._python()
        program = PATH_PROGRAMS.get(language)
        if program is None:
            return None
        if shutil.which(program, path=self._environ.get("PATH", os.defpath)) is None:
            return f"{program} was not found on PATH"
        return None

    def _python(self) -> str | None:
        interpreter = f"{PYTHON_PROJECT}/{PYTHON_INTERPRETER}"
        if (self._workspace / interpreter).exists():
            return None
        return f"{interpreter} is missing; run `{SYNC_FIX}`"
