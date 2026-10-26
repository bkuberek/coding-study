"""Prepares the Python runner (docs/specs/runners.md#invocation).

Python builds nothing: user code runs from `python/practice/` in the workspace, and references are
copied to `.cs/build/python/ref/` (docs/specs/runners.md#reference-materialization). Both run
with the workspace interpreter, whose environment provides `cs_runner` and `cs_support`.

Under `cstudy test --debug` the interpreter runs a short bootstrap that starts debugpy, says so on
standard error, waits for the IDE, and then runs `cs_runner` as `python -m cs_runner` would.
"""

import shutil
from pathlib import Path

from coding_study.adapters.languages.debug_port import require_free_port
from coding_study.adapters.subprocess_tool_probe import SubprocessToolProbe
from coding_study.application.ports import (
    BenchCode,
    BuildScope,
    DebugLaunch,
    Prepared,
    PrepareResult,
    ProgressNotice,
    References,
    RunnerLaunch,
    ToolProbe,
    UserCode,
)
from coding_study.domain.debugging import DEBUG_HOST, DEBUGPY_INSTALL_COMMAND, DebugSession
from coding_study.domain.errors import ContentError, ContentIssue, RunnerStartError
from coding_study.domain.layout import (
    PYTHON_INTERPRETER,
    PYTHON_PROJECT,
    PYTHON_VENV,
    reference_build_path,
)
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS

WORKSPACE_DIRECTORY = PYTHON_PROJECT
RUNNER_MODULE = "cs_runner"
READY_MARKER = "cstudy-debug-agent-listening"
DEBUG_BOOTSTRAP = f"""\
import runpy
import sys

import debugpy

debugpy.listen(("{DEBUG_HOST}", int(sys.argv[1])))
print("{READY_MARKER}", file=sys.stderr, flush=True)
debugpy.wait_for_client()
sys.argv = ["{RUNNER_MODULE}", *sys.argv[2:]]
runpy.run_module("{RUNNER_MODULE}", run_name="__main__", alter_sys=True)
"""
"""`python -c` argument 1 is the port and the rest are the runner's: `-m cs_runner` is
reproduced by `runpy`, with `-X frozen_modules=off` so debugpy can see the standard library's
code."""


class PythonRunner:
    """`LanguageRunner` for Python."""

    def __init__(self, root: Path, probe: ToolProbe | None = None) -> None:
        self._root = root
        self._workspace = root / WORKSPACE_DIRECTORY
        self._probe = probe or SubprocessToolProbe()

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        if isinstance(scope, UserCode) and scope.debug is not None:
            return Prepared(self._debug_launch(scope.debug, notify))
        launch = self._launch()
        if isinstance(scope, References | BenchCode):
            self._materialize(scope)
        return Prepared(launch)

    def _launch(self) -> RunnerLaunch:
        command = (str(self._interpreter()), "-m", RUNNER_MODULE)
        return RunnerLaunch(command, self._workspace, HELLO_TIMEOUT_MS[Language.PYTHON])

    def _debug_launch(self, session: DebugSession, notify: ProgressNotice) -> RunnerLaunch:
        interpreter = self._interpreter()
        self._require_debugpy(interpreter)
        require_free_port(session)
        command = (
            str(interpreter),
            "-X",
            "frozen_modules=off",
            "-c",
            DEBUG_BOOTSTRAP,
            str(session.port),
        )
        debug = DebugLaunch(session, notify, ready_marker=READY_MARKER)
        return RunnerLaunch(command, self._workspace, HELLO_TIMEOUT_MS[Language.PYTHON], debug)

    def _interpreter(self) -> Path:
        interpreter = self._workspace / PYTHON_INTERPRETER
        if not interpreter.exists():
            raise RunnerStartError(
                "the Python workspace is not set up "
                f"({WORKSPACE_DIRECTORY}/{PYTHON_INTERPRETER} is missing): "
                f"run `uv sync --directory {WORKSPACE_DIRECTORY}`"
            )
        return interpreter

    def _require_debugpy(self, interpreter: Path) -> None:
        found = self._probe.run((str(interpreter), "-c", "import debugpy"))
        if found is None or found.exit_code != 0:
            raise RunnerStartError(
                "cannot debug python: debugpy is not installed in "
                f"{WORKSPACE_DIRECTORY}/{PYTHON_VENV}; run `{DEBUGPY_INSTALL_COMMAND}`"
            )

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
