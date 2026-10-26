"""Prepares the Python runner (docs/specs/runners.md#invocation).

Python builds nothing: user code runs from `python/practice/` in the workspace, and references are
copied to `.cs/build/python/ref/` (docs/specs/runners.md#reference-materialization). Both run
with the workspace interpreter, whose environment provides `cs_runner` and `cs_support`.
"""

import shutil
from pathlib import Path

from coding_study.application.ports import (
    BenchCode,
    BuildScope,
    Prepared,
    PrepareResult,
    ProgressNotice,
    References,
    RunnerLaunch,
)
from coding_study.domain.errors import ContentError, ContentIssue, RunnerStartError
from coding_study.domain.layout import PYTHON_INTERPRETER, PYTHON_PROJECT, reference_build_path
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS

WORKSPACE_DIRECTORY = PYTHON_PROJECT
RUNNER_MODULE = "cs_runner"


class PythonRunner:
    """`LanguageRunner` for Python."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._workspace = root / WORKSPACE_DIRECTORY

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        launch = self._launch()
        if isinstance(scope, References | BenchCode):
            self._materialize(scope)
        return Prepared(launch)

    def _launch(self) -> RunnerLaunch:
        interpreter = self._workspace / PYTHON_INTERPRETER
        if not interpreter.exists():
            raise RunnerStartError(
                "the Python workspace is not set up "
                f"({WORKSPACE_DIRECTORY}/{PYTHON_INTERPRETER} is missing): "
                f"run `uv sync --directory {WORKSPACE_DIRECTORY}`"
            )
        command = (str(interpreter), "-m", RUNNER_MODULE)
        return RunnerLaunch(command, self._workspace, HELLO_TIMEOUT_MS[Language.PYTHON])

    def _materialize(self, references: References | BenchCode) -> None:
        for source in references.sources:
            build_path = reference_build_path(references.meta, source.approach_id, Language.PYTHON)
            destination = self._root / build_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(source.path, destination)
            except FileNotFoundError:
                issue = ContentIssue(self._shown(source.path), "", "reference file not found")
                raise ContentError([issue]) from None

    def _shown(self, path: Path) -> str:
        return str(path.relative_to(self._root) if path.is_relative_to(self._root) else path)
