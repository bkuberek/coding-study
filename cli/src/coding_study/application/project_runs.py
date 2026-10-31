"""Running a project problem's jobs (docs/specs/runners.md#project-jobs).

`cstudy test` runs a project's native suite; `cstudy submit` and `cstudy verify` run its grading
job. Both launch the runner in the project folder, one process per job: two projects may define
the same top-level module, and a grading job and a suite job of one project would share it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from coding_study.application.case_materialization import CaseMaterializer
from coding_study.application.comparison import problem_comparator
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    BuildFailed,
    ProgressNotice,
    ProjectGrading,
    ProjectRunner,
    ProjectSuite,
    ProjectTypeChecker,
    Toolchains,
)
from coding_study.domain.config import Config
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError, UsageError
from coding_study.domain.judging import Judgement, RunnableCase, judge
from coding_study.domain.levels import LevelRun, cases_up_to, level_run
from coding_study.domain.naming import symbol_names
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import Language, Problem, ProblemKind, ProblemMeta
from coding_study.domain.project import level_test_file, unsupported_language
from coding_study.domain.runner_grading import graded_signature, grading_target
from coding_study.domain.runs import RunCase, RunJob, RunRequest
from coding_study.domain.suite_runs import SuiteFramework, SuiteJob, SuiteReport

SUITE_JOB = "suite"
SUITE_FRAMEWORKS: Mapping[Language, SuiteFramework | None] = {
    Language.PYTHON: SuiteFramework.PYTEST,
    Language.TYPESCRIPT: SuiteFramework.NODE_TEST,
    Language.JAVA: None,
    Language.KOTLIN: None,
    Language.GO: None,
    Language.RUST: None,
}
"""None: project problems are not yet supported in the language (ADR 0014)."""


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
    """Raises RunnerStartError (exit 4) when the language's runner has no project jobs or the
    toolchain lacks the framework."""
    runner = project_runner(environment.toolchains, run.language)
    launch = runner.prepare_project(ProjectSuite(run.root, run.debug), notify)
    return environment.runner_process.run_suite(launch, suite_job(run, environment.config))


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


@dataclass(frozen=True, slots=True)
class GradingRun:
    """One grading of a project folder (`cstudy submit`, `cstudy verify` D1 and D3)."""

    problem: Problem
    language: Language
    root: Path
    """The project folder: `projects/<slug>/`, or a reference's build copy."""
    level: int
    """Cases of levels 1 to `level` run, against the methods of those levels."""


def run_grading(environment: Environment, run: GradingRun, notify: ProgressNotice) -> Judgement:
    """Judges the project's cases of levels 1 to `run.level` (visible and hidden) with the
    problem's comparator, as `cstudy test` judges any other class job.

    Raises RunnerStartError (exit 4) when the language's runner has no project jobs, ValueError
    for a problem without a `project` block or a language without project problems.
    """
    meta = run.problem.meta
    runner = project_runner(environment.toolchains, run.language)
    graded = replace(run.problem, cases=cases_up_to(run.problem.cases, run.level))
    cases = CaseMaterializer(environment, notify).runnable_cases(graded)
    job = grading_job(run, cases, environment.config)
    launch = runner.prepare_project(ProjectGrading(run.root), notify)
    report = environment.runner_process.run(launch, RunRequest((job,)))
    return judge(cases, report.job(job.job_id), problem_comparator(environment, meta))


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
