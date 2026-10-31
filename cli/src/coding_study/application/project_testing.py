"""`cstudy test` on a project problem: its native suite, as feedback
(docs/specs/cli.md#project-problems).

The suite runs the generated test files of levels 1 to the unlocked level (or `--level`), the
starter's test files and your own. The run is stored in `test_runs`, but it grades nothing and
never opens a level: `cstudy submit` does both.
"""

from dataclasses import dataclass
from datetime import datetime

from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.environment import Environment
from coding_study.application.ports import ProgressNotice
from coding_study.application.project_runs import (
    SUITE_FRAMEWORKS,
    SuiteRun,
    project_levels,
    run_suite,
)
from coding_study.application.run_tests import resolve_debug_session
from coding_study.domain.attempts import Attempt, RunRecord
from coding_study.domain.debugging import DebugRequest, DebugSession
from coding_study.domain.diagnostics import Diagnostic
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
from coding_study.domain.suite_runs import SuiteFramework, SuiteReport
from coding_study.domain.workspace_projects import project_folder

MILLISECONDS_PER_SECOND = 1000


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


@dataclass(frozen=True, slots=True)
class ProjectTestResult:
    meta: ProblemMeta
    attempt: Attempt
    language: Language
    framework: SuiteFramework
    levels: LevelRun
    report: SuiteReport
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

    @property
    def tally(self) -> Tally:
        return suite_tally(self.verdicts)

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Where the project's code did not load (docs/specs/cli.md#diagnostics)."""
        return suite_diagnostics(self.report)

    @property
    def ran(self) -> bool:
        """Some test ran: skipped tests do not count."""
        return self.tally.total > 0

    @property
    def passed(self) -> bool:
        """Every test that ran passed, some test ran, and the suite ran to its end."""
        complete = self.report.load_error is None and self.report.stopped_early is None
        return complete and self.ran and self.tally.all_passed


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
    RunnerStartError (exit 4) when the toolchain cannot run the suite."""
    clock = environment.clock
    started = clock.monotonic()
    attempt = find_attempt(environment.progress, request.slug, request.language)
    language = autograded_language(attempt)
    debug = resolve_debug_session(request.debug, language)
    problem = environment.problems.load(attempt.slug)
    meta = problem.meta
    levels = project_levels(meta, attempt.level_unlocked, request.level)
    folder = project_folder(meta.slug)
    run = SuiteRun(
        meta,
        language,
        environment.workspace.absolute(folder),
        levels.ran_up_to,
        request.case_ids,
        debug,
    )
    suite_started = clock.monotonic()
    report = run_suite(environment, run, notify)
    suite_seconds = clock.monotonic() - suite_started
    verdicts = judge_suite(report.tests, _origins(problem, language, levels))
    if report.load_error is None:
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
    )
    if debug is None:
        _record(environment, result)
    return result


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
