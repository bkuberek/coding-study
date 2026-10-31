"""Launching the TypeScript runner for project jobs (docs/specs/runners.md#launch), and the type
check of a project folder (`cstudy test --typecheck`, docs/specs/cli.md#project-problems)."""

from pathlib import Path

import pytest

from coding_study.adapters.languages.typescript.runner import (
    INSPECTOR_MARKER,
    MAX_DIAGNOSTIC_LINES,
    TypeScriptRunner,
)
from coding_study.application.ports import (
    BuildFailed,
    ProbeResult,
    ProjectGrading,
    ProjectRunner,
    ProjectScope,
    ProjectSuite,
    ProjectTypeChecker,
    RunnerLaunch,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS

PROJECT = Path("projects/bank-project-typescript")
SESSION = DebugSession(Language.TYPESCRIPT, 9229)
PASSED = ProbeResult(0, "")
TYPE_ERROR = (
    "../projects/bank-project-typescript/src/bank.ts(3,5): error TS2322: "
    "Type 'string' is not assignable to type 'number'."
)


class FakeTypeChecker:
    def __init__(self, result: ProbeResult | None = PASSED) -> None:
        self.result = result
        self.calls: list[tuple[Path, tuple[str, ...]]] = []

    def check(self, project: Path, *arguments: str) -> ProbeResult | None:
        self.calls.append((project, arguments))
        return self.result


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A repository root with the TypeScript runner and an installed workspace."""
    (tmp_path / "runners" / "typescript").mkdir(parents=True)
    (tmp_path / "runners" / "typescript" / "runner.ts").write_text("")
    (tmp_path / "typescript" / "node_modules").mkdir(parents=True)
    return tmp_path


def runner(root: Path, checker: FakeTypeChecker | None = None) -> TypeScriptRunner:
    return TypeScriptRunner(root, root / "runners", checker or FakeTypeChecker())


def failed_check(root: Path, output: str) -> BuildFailed:
    """The type check of the project folder when tsc exits 2 after printing `output`."""
    failure = runner(root, FakeTypeChecker(ProbeResult(2, output))).typecheck_project(
        root / PROJECT
    )
    assert failure is not None
    return failure


def prepare(root: Path, scope: ProjectScope, notices: list[str] | None = None) -> RunnerLaunch:
    notify = (notices if notices is not None else []).append
    return runner(root).prepare_project(scope, notify)


def test_the_typescript_runner_runs_project_jobs(root):
    assert isinstance(runner(root), ProjectRunner)


def test_a_grading_job_runs_node_on_the_runner_script(root):
    launch = prepare(root, ProjectGrading(root / PROJECT))
    assert launch.command == ("node", str(root / "runners" / "typescript" / "runner.ts"))


def test_a_project_job_starts_in_the_project_root(root):
    assert prepare(root, ProjectGrading(root / PROJECT)).cwd == root / PROJECT


def test_a_project_job_gets_the_typescript_hello_timeout(root):
    launch = prepare(root, ProjectGrading(root / PROJECT))
    assert launch.hello_timeout_ms == HELLO_TIMEOUT_MS[Language.TYPESCRIPT]


def test_a_suite_job_launches_like_a_grading_job(root):
    suite = prepare(root, ProjectSuite(root / PROJECT))
    assert suite == prepare(root, ProjectGrading(root / PROJECT))


def test_a_project_job_needs_the_runner_script(root):
    (root / "runners" / "typescript" / "runner.ts").unlink()
    with pytest.raises(RunnerStartError, match=r"runner\.ts"):
        prepare(root, ProjectGrading(root / PROJECT))


def test_a_debugged_suite_waits_for_the_inspector_before_running_the_tests(root):
    script = str(root / "runners" / "typescript" / "runner.ts")
    launch = prepare(root, ProjectSuite(root / PROJECT, SESSION))
    assert launch.command == ("node", "--inspect-wait=127.0.0.1:9229", script)


def test_a_debugged_suite_starts_in_the_project_root(root):
    assert prepare(root, ProjectSuite(root / PROJECT, SESSION)).cwd == root / PROJECT


def test_a_debugged_suite_waits_for_the_inspectors_ready_line(root):
    debug = prepare(root, ProjectSuite(root / PROJECT, SESSION)).debug
    assert debug is not None
    assert debug.ready_marker == INSPECTOR_MARKER


def test_the_typescript_runner_type_checks_project_folders(root):
    assert isinstance(runner(root), ProjectTypeChecker)


def test_the_type_check_runs_the_workspaces_tsc_on_the_folders_tsconfig(root):
    checker = FakeTypeChecker()
    runner(root, checker).typecheck_project(root / PROJECT)
    assert checker.calls == [(root / "typescript", ("-p", "../projects/bank-project-typescript"))]


def test_a_folder_that_type_checks_has_no_build_failure(root):
    assert runner(root).typecheck_project(root / PROJECT) is None


def test_type_errors_fail_the_build_with_paths_relative_to_the_workspace(root):
    assert failed_check(root, TYPE_ERROR + "\n").diagnostics == (
        "projects/bank-project-typescript/src/bank.ts(3,5): error TS2322: "
        "Type 'string' is not assignable to type 'number'.",
    )


def test_every_diagnostic_of_the_folder_is_kept_with_its_continuation_lines(root):
    output = f"{TYPE_ERROR}\n  Detail of the error.\nerror TS18003: No inputs were found.\n"
    assert failed_check(root, output).diagnostics[1:] == (
        "  Detail of the error.",
        "error TS18003: No inputs were found.",
    )


def test_diagnostics_are_cut_at_the_limit(root):
    output = "\n".join([TYPE_ERROR] * (MAX_DIAGNOSTIC_LINES + 5))
    assert len(failed_check(root, output).diagnostics) == MAX_DIAGNOSTIC_LINES


def test_the_type_check_needs_the_workspaces_node_modules(root):
    (root / "typescript" / "node_modules").rmdir()
    with pytest.raises(RunnerStartError, match="pnpm install"):
        runner(root).typecheck_project(root / PROJECT)


def test_the_type_check_needs_pnpm(root):
    with pytest.raises(RunnerStartError, match="pnpm is not installed"):
        runner(root, FakeTypeChecker(None)).typecheck_project(root / PROJECT)
