"""Prepares the TypeScript runner (docs/specs/runners.md#invocation).

Node runs the runners' `typescript/runner.ts` directly through type stripping, so user code needs
no build; `cstudy test --typecheck` adds a `tsc --noEmit` pass over the workspace's `typescript/`
project. References are copied into `.cs/build/typescript/`, a project that maps `#support` like
the workspace.

`cstudy test --debug` starts Node with `--inspect-wait` on the loopback interface: the runner script
begins only once the IDE attached, and Node keeps the line and column of the `.ts` file.
"""

import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Protocol

from coding_study.adapters.languages.debug_port import require_free_port
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    BuildScope,
    DebugLaunch,
    Prepared,
    PrepareResult,
    ProbeResult,
    ProgressNotice,
    References,
    ReferenceSource,
    RunnerLaunch,
    UserCode,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import ContentError, ContentIssue, RunnerStartError
from coding_study.domain.layout import (
    BUILD_DIRECTORY,
    TYPESCRIPT_PROJECT,
    reference_build_path,
    stub_path,
)
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import HELLO_TIMEOUT_MS

NODE = "node"
EXPOSE_GC_FLAG = "--expose-gc"
INSPECTOR_MARKER = "Debugger listening on"
"""What Node prints to standard error once the inspector listens."""
RUNNER_SCRIPT = "typescript/runner.ts"
SUPPORT_MODULE = "typescript/support.ts"
"""Relative to the runners directory."""
WORKSPACE_PROJECT = TYPESCRIPT_PROJECT
BUILD_PROJECT = f"{BUILD_DIRECTORY}/typescript"
PACKAGE_FILE = "package.json"
SUPPORT_FILE = "support.ts"
DEPENDENCIES_DIRECTORY = "node_modules"
TYPECHECK_COMMAND = ("pnpm", "exec", "tsc", "--noEmit", "--pretty", "false")
TYPECHECK_NOTE = "tsc"
TYPECHECK_TIMEOUT_SECONDS = 120.0
MAX_DIAGNOSTIC_LINES = 40
BUILD_PACKAGE = {
    "private": True,
    "type": "module",
    "imports": {"#support": f"./{SUPPORT_FILE}"},
}
"""Mirrors the workspace package.json fields that make `#support` resolve."""


class TypeChecker(Protocol):
    def check(self, project: Path) -> ProbeResult | None:
        """Type-check the TypeScript project; None when the tool is not installed."""
        ...


class PnpmTypeChecker:
    """Runs the project's own `tsc --noEmit` through pnpm (docs/specs/cli.md, `--typecheck`)."""

    def check(self, project: Path) -> ProbeResult | None:
        try:
            completed = subprocess.run(
                TYPECHECK_COMMAND,
                cwd=project,
                capture_output=True,
                text=True,
                timeout=TYPECHECK_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError:
            return None
        return ProbeResult(completed.returncode, completed.stdout + completed.stderr)


class TypeScriptRunner:
    """`LanguageRunner` for TypeScript."""

    def __init__(self, root: Path, runners: Path, type_checker: TypeChecker) -> None:
        self._root = root
        self._runners = runners
        self._type_checker = type_checker

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        match scope:
            case References():
                return self._prepare_references(scope)
            case BenchCode():
                return self._prepare_bench(scope)
            case UserCode():
                return self._prepare_user_code(scope, notify)

    def _prepare_bench(self, scope: BenchCode) -> PrepareResult:
        """References and user code in one Node process with `gc()` exposed for memory figures."""
        self._materialize(scope.meta, scope.sources)
        project = BUILD_PROJECT if scope.references_only else WORKSPACE_PROJECT
        return Prepared(self._launch(self._root / project, EXPOSE_GC_FLAG))

    def _prepare_user_code(self, scope: UserCode, notify: ProgressNotice) -> PrepareResult:
        workspace = self._root / WORKSPACE_PROJECT
        if not (workspace / PACKAGE_FILE).is_file():
            raise RunnerStartError(f"{WORKSPACE_PROJECT}/{PACKAGE_FILE} is missing")
        launch = (
            self._launch(workspace)
            if scope.debug is None
            else self._debug_launch(workspace, scope.debug, notify)
        )
        if not scope.typecheck:
            return Prepared(launch)
        user_file = PurePosixPath(stub_path(scope.meta, Language.TYPESCRIPT))
        diagnostics = self._typecheck(workspace, str(user_file.relative_to(WORKSPACE_PROJECT)))
        if diagnostics:
            return BuildFailed(diagnostics)
        return Prepared(launch, build_note=TYPECHECK_NOTE)

    def _typecheck(self, workspace: Path, user_file: str) -> tuple[str, ...]:
        if not (workspace / DEPENDENCIES_DIRECTORY).is_dir():
            raise RunnerStartError(f"run pnpm install in {WORKSPACE_PROJECT} to type-check")
        result = self._type_checker.check(workspace)
        if result is None:
            raise RunnerStartError("pnpm is not installed; --typecheck runs pnpm exec tsc")
        if result.exit_code == 0:
            return ()
        return user_file_diagnostics(result.output, user_file)

    def _prepare_references(self, scope: References) -> PrepareResult:
        self._materialize(scope.meta, scope.sources)
        return Prepared(self._launch(self._root / BUILD_PROJECT))

    def _materialize(self, meta: ProblemMeta, sources: tuple[ReferenceSource, ...]) -> None:
        _write_build_project(self._root / BUILD_PROJECT, self._runners / SUPPORT_MODULE)
        for source in sources:
            relative = reference_build_path(meta, source.approach_id, Language.TYPESCRIPT)
            _copy_reference(self._root / source.path, self._root / relative)

    def _debug_launch(
        self, workspace: Path, session: DebugSession, notify: ProgressNotice
    ) -> RunnerLaunch:
        require_free_port(session)
        launch = self._launch(workspace, f"--inspect-wait={session.address}")
        return replace(launch, debug=DebugLaunch(session, notify, ready_marker=INSPECTOR_MARKER))

    def _launch(self, cwd: Path, *node_flags: str) -> RunnerLaunch:
        script = self._runners / RUNNER_SCRIPT
        if not script.is_file():
            raise RunnerStartError(f"the TypeScript runner is missing: {script}")
        command = (NODE, *node_flags, str(script))
        return RunnerLaunch(command, cwd, HELLO_TIMEOUT_MS[Language.TYPESCRIPT])


def user_file_diagnostics(output: str, user_file: str) -> tuple[str, ...]:
    """`tsc --pretty false` lines about `user_file` (with their indented continuation lines).

    Errors only in other practice files are dropped, so they never block this problem.
    """
    kept: list[str] = []
    keeping = False
    for line in output.splitlines():
        if not line.startswith(" "):
            keeping = line.startswith(f"{user_file}(")
        if keeping:
            kept.append(line)
    return tuple(kept[:MAX_DIAGNOSTIC_LINES])


def _write_build_project(project: Path, support: Path) -> None:
    """`support.ts` re-exports the runners' support module by a path relative to `project`."""
    project.mkdir(parents=True, exist_ok=True)
    (project / PACKAGE_FILE).write_text(json.dumps(BUILD_PACKAGE, indent=2) + "\n")
    relative = Path(os.path.relpath(support, project)).as_posix()
    (project / SUPPORT_FILE).write_text(f'export * from "{relative}";\n')


def _copy_reference(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise ContentError([ContentIssue(str(source), "", "reference file not found")])
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
