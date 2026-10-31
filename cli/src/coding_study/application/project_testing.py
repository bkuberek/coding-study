"""`cstudy test` on a project problem: its native suite, as feedback
(docs/specs/cli.md#project-problems).

The suite runs the generated test files of levels 1 to the unlocked level (or `--level`), the
starter's test files and your own. With `--typecheck` the folder's type check comes first, and a
failure runs no test. The run is stored in `test_runs`, but it grades nothing and never opens a
level: `cstudy submit` does both.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.environment import Environment
from coding_study.application.ports import BuildFailed, ProgressNotice
from coding_study.application.project_runs import (
    SUITE_FRAMEWORKS,
    SuiteRun,
    project_levels,
    run_suite,
    typecheck_project,
)
from coding_study.application.run_tests import resolve_debug_session
from coding_study.domain.attempts import Attempt, RunRecord
from coding_study.domain.debugging import DebugRequest, DebugSession
from coding_study.domain.diagnostics import Diagnostic, DiagnosticParser, DiagnosticSource
from coding_study.domain.diagnostics_tsc import TscReport
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.levels import FIRST_LEVEL, LevelRun
from coding_study.domain.problem import Language, Problem, ProblemKind, ProblemMeta
from coding_study.domain.project import level_test_file
from coding_study.domain.project_test_runs import (
    SuiteOrigins,
    SuiteTestVerdict,
    judge_suite,
    suite_diagnostics,
    suite_tally,
    unmatched_selections,
)
from coding_study.domain.runs import UserError
from coding_study.domain.suite_runs import SuiteFramework, SuiteReport, SuiteTest
from coding_study.domain.workspace_projects import project_folder

MILLISECONDS_PER_SECOND = 1000
TYPECHECK_REPORTS: Mapping[Language, Callable[[str], DiagnosticParser] | None] = {
    Language.PYTHON: None,
    Language.TYPESCRIPT: TscReport,
    Language.JAVA: None,
    Language.KOTLIN: None,
    Language.GO: None,
    Language.RUST: None,
}
"""How to read each language's type check, given the project folder its paths start with; None:
no parser, so each line of the report is a diagnostic without a place."""


class SuiteVerdictListener(Protocol):
    """Told of each test as it starts, and of its verdict as soon as the runner reports it."""

    def test_started(self, test_id: str) -> None: ...

    def test_judged(self, verdict: SuiteTestVerdict) -> None: ...


@dataclass(frozen=True, slots=True)
class ProjectTestRequest:
    slug: str | None = None
    language: Language | None = None
    case_ids: tuple[str, ...] = ()
    """`--case`: test ids, or their last part; empty runs every test."""
    level: int | None = None
    """`--level N`: the generated files of levels 1 to N; None runs every unlocked level's."""
    debug: DebugRequest | None = None
    """`--debug`: the suite runs under an IDE debugger and is not recorded."""
    listener: SuiteVerdictListener | None = None
    """`--events`: hears each test while the suite runs."""
    typecheck: bool = False
    """`--typecheck`: type-check the folder first; a failure runs no test."""


@dataclass(frozen=True, slots=True)
class ProjectTestResult:
    meta: ProblemMeta
    attempt: Attempt
    language: Language
    framework: SuiteFramework
    levels: LevelRun
    report: SuiteReport | None
    """None when the type check failed and no test ran."""
    verdicts: tuple[SuiteTestVerdict, ...]
    ran_at: datetime
    suite_seconds: float
    """The runner's part of the run."""
    duration_seconds: float
    every_case: bool
    """False with `--case`, or `--level` below the unlocked level."""
    watched: str
    """The project folder, relative to the workspace root."""
    debug: DebugSession | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
    """Where the project's code did not type-check or load (docs/specs/cli.md#diagnostics)."""
    build_failure: BuildFailed | None = None
    """`--typecheck`: the type check's report, when it failed."""

    @property
    def load_error(self) -> UserError | None:
        """The framework could not run the suite."""
        return self.report.load_error if self.report else None

    @property
    def stopped_early(self) -> str | None:
        """Why the tests not reported never ran; None when the suite ran to its end."""
        return self.report.stopped_early if self.report else None

    @property
    def tally(self) -> Tally:
        return suite_tally(self.verdicts)

    @property
    def every_level_done(self) -> bool:
        """A submission already passed every case of every level: the full pass."""
        return self.attempt.first_pass_at is not None

    @property
    def ran(self) -> bool:
        """Some test ran: skipped tests do not count."""
        return self.tally.total > 0

    @property
    def passed(self) -> bool:
        """The folder type-checked, every test that ran passed, some test ran, and the suite ran
        to its end."""
        complete = self.report is not None and self.load_error is None
        return complete and self.stopped_early is None and self.ran and self.tally.all_passed


def is_project_attempt(
    environment: Environment, slug: str | None, language: Language | None
) -> bool:
    """Whether the attempt a command works on is at a project problem.

    Raises UsageError without an attempt in progress.
    """
    attempt = find_attempt(environment.progress, slug, language)
    if attempt.language is None:
        return False
    return environment.problems.load(attempt.slug).meta.kind is ProblemKind.PROJECT


def run_project_tests(
    environment: Environment, request: ProjectTestRequest, notify: ProgressNotice
) -> ProjectTestResult:
    """Raises UsageError for a locked level or a `--case` that names no test, and
    RunnerStartError (exit 4) when the toolchain cannot type-check the folder or run the suite."""
    clock = environment.clock
    started = clock.monotonic()
    attempt = find_attempt(environment.progress, request.slug, request.language)
    language = autograded_language(attempt)
    debug = resolve_debug_session(request.debug, language)
    problem = environment.problems.load(attempt.slug)
    meta = problem.meta
    levels = project_levels(meta, attempt.level_unlocked, request.level)
    folder = project_folder(meta.slug)
    root = environment.workspace.absolute(folder)
    failure = typecheck_project(environment, language, root) if request.typecheck else None
    origins = _origins(problem, language, levels)
    listener = request.listener
    run = SuiteRun(
        meta,
        language,
        root,
        levels.ran_up_to,
        request.case_ids,
        debug,
        _TestJudge(origins, listener) if listener else None,
    )
    suite_started = clock.monotonic()
    report = None if failure else run_suite(environment, run, notify)
    suite_seconds = clock.monotonic() - suite_started
    verdicts = judge_suite(report.tests, origins) if report else ()
    if report is not None and report.load_error is None:
        _require_matches(verdicts, request.case_ids)
    framework = SUITE_FRAMEWORKS[language]
    assert framework is not None
    result = ProjectTestResult(
        meta=meta,
        attempt=attempt,
        language=language,
        framework=framework,
        levels=levels,
        report=report,
        verdicts=verdicts,
        ran_at=clock.now(),
        suite_seconds=suite_seconds,
        duration_seconds=clock.monotonic() - started,
        every_case=not request.case_ids and levels.ran_up_to == levels.unlocked,
        watched=folder,
        debug=debug,
        diagnostics=(
            suite_diagnostics(report, str(root))
            if report
            else _typecheck_diagnostics(failure, language, folder)
        ),
        build_failure=failure,
    )
    if debug is None:
        _record(environment, result)
    return result


class _TestJudge:
    """Judges each test the runner reports, as `run_project_tests` judges them all at the end."""

    def __init__(self, origins: SuiteOrigins, listener: SuiteVerdictListener) -> None:
        self._origins = origins
        self._listener = listener

    def test_started(self, test_id: str) -> None:
        self._listener.test_started(test_id)

    def test_finished(self, test: SuiteTest) -> None:
        (verdict,) = judge_suite((test,), self._origins)
        self._listener.test_judged(verdict)


def _typecheck_diagnostics(
    failure: BuildFailed | None, language: Language, folder: str
) -> tuple[Diagnostic, ...]:
    """The type check's report read by its language's parser, else one diagnostic per line."""
    if failure is None:
        return ()
    report = TYPECHECK_REPORTS[language]
    if report is None:
        source = DiagnosticSource.TYPECHECK
        return tuple(Diagnostic(line, source) for line in failure.diagnostics)
    return report(folder).parse("\n".join(failure.diagnostics))


def _origins(problem: Problem, language: Language, levels: LevelRun) -> SuiteOrigins:
    project = problem.meta.project
    assert project is not None
    files = problem.project_files
    starter = files.starter.paths if files and files.starter else frozenset[str]()
    level_files = {
        level_test_file(project, language, level): level
        for level in range(FIRST_LEVEL, levels.unlocked + 1)
    }
    return SuiteOrigins(level_files, starter)


def _require_matches(verdicts: tuple[SuiteTestVerdict, ...], case_ids: tuple[str, ...]) -> None:
    unmatched = unmatched_selections([verdict.test.test_id for verdict in verdicts], case_ids)
    if unmatched:
        raise UsageError(f"no test matches --case {unmatched[0]}")


def _record(environment: Environment, result: ProjectTestResult) -> None:
    """Stores the run; it changes nothing else on the attempt."""
    environment.progress.add_test_run(
        RunRecord(
            attempt_id=result.attempt.id,
            ran_at=result.ran_at,
            code_hash=environment.workspace.content_hash(result.watched),
            tally=result.tally,
            duration_ms=round(result.duration_seconds * MILLISECONDS_PER_SECOND),
        )
    )
