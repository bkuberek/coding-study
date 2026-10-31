"""Stand-ins for a project problem's runner, its suite runs and its grading runs, and an
environment on the fixture project problem (docs/specs/runners.md#project-jobs)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    BuildScope,
    PrepareResult,
    ProgressNotice,
    ProjectScope,
    RunnerLaunch,
)
from coding_study.domain.problem import Language
from coding_study.domain.runs import (
    CaseOutcome,
    CaseReport,
    JobReport,
    RunCase,
    RunJob,
    RunnerInfo,
    RunReport,
    RunRequest,
    UserError,
)
from coding_study.domain.suite_runs import Passed, SuiteJob, SuiteReport, SuiteTest
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import PROJECT_PROBLEMS

PROJECT_SLUG = "bank-project-python"
PROJECT_FOLDER = f"projects/{PROJECT_SLUG}"
PROJECT_RUNNER = RunnerInfo("python", 1, "3.13", ("project", "suite"))
LEVEL_1_TEST = SuiteTest("tests/test_level_1.py::test_ex1", Passed(1000))

type GradingAnswer = Callable[[RunJob, RunCase], CaseOutcome]


@dataclass
class FakeProjectRunner:
    """Launches every project job in its root; never builds."""

    scopes: list[ProjectScope] = field(default_factory=list[ProjectScope])

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise AssertionError("a project job is prepared with prepare_project")

    def prepare_project(self, scope: ProjectScope, notify: ProgressNotice) -> RunnerLaunch:
        self.scopes.append(scope)
        return RunnerLaunch(("python",), scope.root, 5_000)


def unanswered(job: RunJob, case: RunCase) -> CaseOutcome:
    raise AssertionError(f"no scripted answer for case {case.id}")


@dataclass
class ScriptedProjectProcess:
    """Reports `tests` for every suite, and answers every graded case with `answer`; a grading
    job fails to load with `load_error` when it is set."""

    tests: tuple[SuiteTest, ...] = (LEVEL_1_TEST,)
    answer: GradingAnswer = unanswered
    load_error: UserError | None = None
    suites: list[SuiteJob] = field(default_factory=list[SuiteJob])
    gradings: list[RunJob] = field(default_factory=list[RunJob])

    def run_suite(self, launch: RunnerLaunch, job: SuiteJob) -> SuiteReport:
        self.suites.append(job)
        return SuiteReport(PROJECT_RUNNER, self.tests)

    def run(self, launch: RunnerLaunch, request: RunRequest) -> RunReport:
        self.gradings.extend(request.jobs)
        return RunReport(PROJECT_RUNNER, tuple(self._job(job) for job in request.jobs))

    def _job(self, job: RunJob) -> JobReport:
        if self.load_error is not None:
            return JobReport(job.job_id, load_error=self.load_error)
        return JobReport(
            job.job_id, tuple(CaseReport(case.id, self.answer(job, case)) for case in job.cases)
        )


def project_environment(
    tmp_path: Path, process: ScriptedProjectProcess, **overrides: object
) -> Environment:
    """The fixture project problem, its Python runner faked and its tests generated for real."""
    toolchains = FakeToolchains(
        runners={Language.PYTHON: FakeProjectRunner()},
        project_test_generators={Language.PYTHON: PythonTestGenerator()},
    )
    parts: Mapping[str, object] = {"toolchains": toolchains, "runner_process": process}
    root = repository_root(tmp_path, PROJECT_PROBLEMS)
    return make_environment(root, **{**parts, **overrides})
