"""Running a project problem's jobs (docs/specs/runners.md#project-jobs).

`cstudy test` runs a project's native suite and `cstudy submit` its grading job. Both launch the
runner in the project folder, one process per job: two projects may define the same top-level
module, and a grading job and a suite job of one project would share it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from coding_study.application.environment import Environment
from coding_study.application.ports import (
    ProgressNotice,
    ProjectRunner,
    ProjectSuite,
    Toolchains,
)
from coding_study.domain.config import Config
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.project import level_test_file, unsupported_language
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


def run_suite(environment: Environment, run: SuiteRun, notify: ProgressNotice) -> SuiteReport:
    """Raises RunnerStartError (exit 4) when the language's runner has no project jobs or the
    toolchain lacks the framework."""
    runner = project_runner(environment.toolchains, run.language)
    launch = runner.prepare_project(ProjectSuite(run.root, run.debug), notify)
    return environment.runner_process.run_suite(launch, suite_job(run, environment.config))


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
