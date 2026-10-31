"""Running a project problem's jobs (docs/specs/runners.md#project-jobs).

`cstudy test` runs a project's native suite; `cstudy submit` and `cstudy verify` run its grading
job. Both launch the runner in the project folder, one process per job: two projects may define
the same top-level module, and a grading job and a suite job of one project would share it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from coding_study.application.case_materialization import CaseMaterializer
from coding_study.application.comparison import problem_comparator
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    BuildFailed,
    HostedSuite,
    ProgressNotice,
    ProjectGrading,
    ProjectRunner,
    ProjectSuite,
    ProjectSuiteHost,
    ProjectTypeChecker,
    SuiteListener,
    Toolchains,
)
from coding_study.domain.comparators import Comparator
from coding_study.domain.config import Config
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError, UsageError
from coding_study.domain.judging import CaseVerdict, Judgement, RunnableCase, judge
from coding_study.domain.levels import LevelRun, cases_up_to, level_run
from coding_study.domain.naming import symbol_names
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import Language, Problem, ProblemKind, ProblemMeta
from coding_study.domain.project import level_test_file, unsupported_language
from coding_study.domain.runner_grading import graded_signature, grading_target
from coding_study.domain.runs import (
    CaseReport,
    JobReport,
    RunCase,
    RunJob,
    RunRequest,
    UserError,
)
from coding_study.domain.suite_runs import SuiteFramework, SuiteJob, SuiteReport

SUITE_JOB = "suite"
SUITE_FRAMEWORKS: Mapping[Language, SuiteFramework | None] = {
    Language.PYTHON: SuiteFramework.PYTEST,
    Language.TYPESCRIPT: SuiteFramework.NODE_TEST,
    Language.JAVA: SuiteFramework.JUNIT_PLATFORM,
    Language.KOTLIN: SuiteFramework.JUNIT_PLATFORM,
    Language.GO: SuiteFramework.GO_TEST,
    Language.RUST: SuiteFramework.LIBTEST,
}
"""None: project problems are not yet supported in the language (ADR 0014)."""
COMPILE_ERROR = "CompileError"
DOES_NOT_COMPILE = "the project does not compile"


@dataclass(frozen=True, slots=True)
class SuiteRun:
    """One run of a project folder's native tests (`cstudy test`, `cstudy verify` D9)."""

    meta: ProblemMeta
    language: Language
    root: Path
    """The project folder: `projects/<slug>/`, or a reference's build copy."""
    level: int
    """The generated test files of the levels above it are left out (`cstudy test --level`)."""
    select: tuple[str, ...] = ()
    """`cstudy test --case`: test ids, or their last part."""
    debug: DebugSession | None = None
    listener: SuiteListener | None = None
    """Hears each test as the runner reports it."""


def project_levels(meta: ProblemMeta, unlocked: int | None, requested: int | None) -> LevelRun:
    """The levels a project command covers: 1 to `requested`, or to the unlocked level.

    Raises UsageError for a level the problem lacks or one still locked.
    """
    try:
        levels = level_run(meta, unlocked, requested)
    except ValueError as error:
        raise UsageError(str(error)) from None
    if levels is None:
        raise ValueError(f"{meta.slug} has no levels")
    return levels


def run_suite(environment: Environment, run: SuiteRun, notify: ProgressNotice) -> SuiteReport:
    """Through the runner process, or, for a language that runs each test as a process of its
    own (Rust), through the language's runner itself.

    Raises RunnerStartError (exit 4) when the language's runner has no project jobs or the
    toolchain lacks the framework.
    """
    runner = project_runner(environment.toolchains, run.language)
    job = suite_job(run, environment.config)
    if isinstance(runner, ProjectSuiteHost):
        hosted = HostedSuite(run.meta.slug, job, run.debug, run.listener)
        return runner.run_project_suite(hosted, notify)
    suite = ProjectSuite(run.root, run.debug, run.meta, job.exclude)
    prepared = runner.prepare_project(suite, notify)
    if isinstance(prepared, BuildFailed):
        return SuiteReport(None, load_error=compile_error(prepared))
    return environment.runner_process.run_suite(prepared, job, run.listener)


def typecheck_project(
    environment: Environment, language: Language, root: Path
) -> BuildFailed | None:
    """`cstudy test --typecheck` on the project folder at `root`: its language's type check of
    the whole folder, a build step of its own (docs/specs/cli.md#project-problems). None when the
    folder type-checks, or when its language has no type check apart from running it.

    Raises RunnerStartError (exit 4) for a language without project jobs, or a workspace that
    cannot type-check.
    """
    runner = project_runner(environment.toolchains, language)
    if not isinstance(runner, ProjectTypeChecker):
        return None
    return runner.typecheck_project(root)


def project_runner(toolchains: Toolchains, language: Language) -> ProjectRunner:
    """Raises RunnerStartError (exit 4) for a language whose runner has no project jobs yet."""
    runner = toolchains.runner(language)
    if not isinstance(runner, ProjectRunner):
        raise RunnerStartError(f"the {language} runner does not run project problems yet")
    return runner


def suite_job(run: SuiteRun, config: Config) -> SuiteJob:
    """Raises ValueError for a problem without a `project` block or a language without suites."""
    meta = run.meta
    if meta.project is None:
        raise ValueError(f"{meta.slug} is not a project problem")
    framework = SUITE_FRAMEWORKS[run.language]
    if framework is None:
        raise ValueError(unsupported_language(run.language))
    locked = range(run.level + 1, len(meta.levels) + 1)
    return SuiteJob(
        job_id=f"{meta.slug}/{SUITE_JOB}",
        framework=framework,
        root=str(run.root),
        hang_guard_ms=resolve_hang_guard_ms(config, None, meta.hang_guard_ms),
        exclude=tuple(level_test_file(meta.project, run.language, level) for level in locked),
        select=run.select,
    )


class CaseVerdictListener(Protocol):
    """Told of each graded case as it starts, and of its verdict as soon as the runner reports
    the case's outcome."""

    def case_started(self, case: RunnableCase) -> None: ...

    def case_judged(self, verdict: CaseVerdict) -> None: ...


@dataclass(frozen=True, slots=True)
class GradingRun:
    """One grading of a project folder (`cstudy submit`, `cstudy verify` D1 and D3)."""

    problem: Problem
    language: Language
    root: Path
    """The project folder: `projects/<slug>/`, or a reference's build copy."""
    level: int
    """Cases of levels 1 to `level` run, against the methods of those levels."""
    listener: CaseVerdictListener | None = None


def run_grading(environment: Environment, run: GradingRun, notify: ProgressNotice) -> Judgement:
    """Judges the project's cases of levels 1 to `run.level` (visible and hidden) with the
    problem's comparator, as `cstudy test` judges any other class job. A project whose code does
    not compile has a load error in place of every case.

    Raises RunnerStartError (exit 4) when the language's runner has no project jobs, ValueError
    for a problem without a `project` block or a language without project problems.
    """
    runner = project_runner(environment.toolchains, run.language)
    graded = replace(run.problem, cases=cases_up_to(run.problem.cases, run.level))
    cases = CaseMaterializer(environment, notify).runnable_cases(graded)
    job = grading_job(run, cases, environment.config)
    comparator = problem_comparator(environment, run.problem.meta)
    grading = ProjectGrading(run.root, run.problem.meta, run.level)
    prepared = runner.prepare_project(grading, notify)
    if isinstance(prepared, BuildFailed):
        return judge(cases, JobReport(job.job_id, load_error=compile_error(prepared)), comparator)
    judging = _CaseJudge(cases, comparator, run.listener) if run.listener else None
    report = environment.runner_process.run(prepared, RunRequest((job,)), judging)
    return judge(cases, report.job(job.job_id), comparator)


def compile_error(failure: BuildFailed) -> UserError:
    """A project that does not compile, as the load error of the job it never ran: the compiler's
    lines are its trace (docs/specs/runners.md#jvm-project-builds)."""
    return UserError(COMPILE_ERROR, DOES_NOT_COMPILE, "\n".join(failure.diagnostics))


class _CaseJudge:
    """Judges each case the runner reports, as `run_grading` judges them all at the end."""

    def __init__(
        self, cases: Sequence[RunnableCase], comparator: Comparator, listener: CaseVerdictListener
    ) -> None:
        self._cases = {case.id: case for case in cases}
        self._comparator = comparator
        self._listener = listener

    def case_started(self, job_id: str, case_id: str) -> None:
        self._listener.case_started(self._cases[case_id])

    def case_finished(self, job_id: str, report: CaseReport) -> None:
        case = self._cases[report.case_id]
        judged = judge((case,), JobReport(job_id, (report,)), self._comparator)
        self._listener.case_judged(judged.verdicts[0])


def grading_job(run: GradingRun, cases: Sequence[RunnableCase], config: Config) -> RunJob:
    """Raises ValueError for a problem without a `project` block or a language without project
    problems."""
    meta = run.problem.meta
    if meta.project is None:
        raise ValueError(f"{meta.slug} is not a project problem")
    signature = graded_signature(meta.signature, run.level)
    return RunJob(
        job_id=meta.slug,
        kind=ProblemKind.PROJECT,
        target=grading_target(meta.project, run.language, str(run.root)),
        names=symbol_names(signature, run.language),
        signature=signature,
        cases=tuple(_run_case(case, meta, config) for case in cases),
    )


def _run_case(case: RunnableCase, meta: ProblemMeta, config: Config) -> RunCase:
    hang_guard_ms = resolve_hang_guard_ms(config, case.hang_guard_ms, meta.hang_guard_ms)
    return RunCase(case.id, case.input, hang_guard_ms)
