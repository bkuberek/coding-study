"""Stand-ins for a project problem's runner, its suite runs and its grading runs, its project test
generator, and an environment on the fixture project problem
(docs/specs/runners.md#project-jobs)."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    BuildScope,
    CaseListener,
    PrepareResult,
    ProgressNotice,
    ProjectScope,
    ProjectTestGenerator,
    RunnerLaunch,
    SuiteListener,
)
from coding_study.application.verify_projects import STARTER_BUILDS
from coding_study.domain.cases import JsonValue, OperationSequence
from coding_study.domain.problem import Language, Problem
from coding_study.domain.project_tests import LevelTests
from coding_study.domain.runs import (
    CaseOutcome,
    CaseReport,
    JobReport,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunnerInfo,
    RunReport,
    RunRequest,
    StressCompleted,
    StressRun,
    UserError,
)
from coding_study.domain.suite_runs import Passed, SuiteJob, SuiteReport, SuiteTest
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import PROJECT_PROBLEMS, PROJECT_STRESS_PROBLEMS

PROJECT_SLUG = "bank-project-python"
TALLY_SLUG = "tally-project-python"
"""The project with stress cases (`stress_project_environment`)."""
PROJECT_FOLDER = f"projects/{PROJECT_SLUG}"
PROJECT_RUNNER = RunnerInfo("python", 1, "3.13", ("project", "suite"))
LEVEL_1_TEST = SuiteTest("tests/test_level_1.py::test_ex1", Passed(1000))
NOT_IMPLEMENTED = UserError("NotImplementedError", "")

type GradingAnswer = Callable[[RunJob, RunCase], CaseOutcome]


class FakeTestGenerator:
    """One line per visible case, so a test can tell what was generated."""

    def generate(self, tests: LevelTests) -> str:
        names = "".join(f"test {test.case_id}\n" for test in tests.tests)
        return f"# level {tests.level} of {tests.slug}\n{names}"


@dataclass
class FakeProjectRunner:
    """Launches every project job in the root it was prepared for; never builds."""

    scopes: list[ProjectScope] = field(default_factory=list[ProjectScope])

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise AssertionError("a project job is prepared with prepare_project")

    def prepare_project(self, scope: ProjectScope, notify: ProgressNotice) -> RunnerLaunch:
        self.scopes.append(scope)
        return RunnerLaunch(("python",), scope.root, 5_000)


def project_toolchains(
    generator: ProjectTestGenerator, runner: FakeProjectRunner | None = None
) -> FakeToolchains:
    """Python's toolchains for project problems: `runner` (default: a new one) and `generator`."""
    return FakeToolchains(
        runners={Language.PYTHON: runner or FakeProjectRunner()},
        project_test_generators={Language.PYTHON: generator},
    )


def unanswered(job: RunJob, case: RunCase) -> CaseOutcome:
    raise AssertionError(f"no scripted answer for case {case.id}")


def raises_not_implemented(job: RunJob, case: RunCase) -> CaseOutcome:
    return Raised(NOT_IMPLEMENTED, 1_000)


def expected_answers(*problems: Problem) -> GradingAnswer:
    """Answers every case with the problem's expected output; a problem's slug is the id of its
    grading job."""
    expected: Mapping[str, Mapping[str, JsonValue]] = {
        problem.meta.slug: {
            case.id: case.expected.value for case in problem.cases if case.expected is not None
        }
        for problem in problems
    }
    return lambda job, case: Returned(expected[job.job_id][case.id], 1_000)


class TallyModel:
    """The stress fixture's `Tally` run one call at a time: what a correct project returns."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def call(self, op: str, args: tuple[JsonValue, ...]) -> JsonValue:
        key = args[0]
        assert isinstance(key, str)
        if op == "count":
            return self._counts.get(key, 0)
        amount = args[1]
        assert isinstance(amount, int)
        count = self._counts.get(key, 0)
        if op == "add":
            self._counts[key] = count + amount
            return count + amount
        if count < amount:
            return False
        self._counts[key] = count - amount
        return True

    def outputs(self, ops: OperationSequence, first: int) -> tuple[JsonValue, ...]:
        """The outputs of `ops`, the first `first` of them constructors or harness ops."""
        calls = zip(ops.ops[first:], ops.args[first:], strict=True)
        return (None,) * first + tuple(self.call(op, args) for op, args in calls)


def correct_stress(run: StressRun) -> StressCompleted:
    """A stress run of the stress fixture as a correct project completes it: its workers' calls
    one after another."""
    model = TallyModel()
    setup = model.outputs(run.setup, 1)
    workers = tuple(model.outputs(worker, 0) for worker in run.workers)
    final = model.outputs(run.final, 0) if run.final else ()
    return StressCompleted(setup, workers, final, {}, 2_000_000)


def tally_answers(problem: Problem, *, racy: bool = False) -> GradingAnswer:
    """Every case of the stress fixture as a correct project answers it; a racy one returns the
    same count twice in every run of `s1`."""
    expected = {case.id: case.expected for case in problem.cases}

    def answer(job: RunJob, case: RunCase) -> CaseOutcome:
        if isinstance(case.input, StressRun):
            completed = correct_stress(case.input)
            if racy and case.id.startswith("s1"):
                first, *rest = completed.workers
                completed = replace(completed, workers=((first[1], *first[1:]), *rest))
            return completed
        wanted = expected[case.id]
        assert wanted is not None
        return Returned(wanted.value, 1_000)

    return answer


@dataclass
class ScriptedProjectProcess:
    """Reports `tests` for every suite, and answers every graded case with `answer`, telling the
    listener of each test and case as a runner would.

    A grading job fails to load with `load_error` when it is set; a suite does not run with
    `suite_load_error`, and stops with `stopped_early`.
    """

    tests: tuple[SuiteTest, ...] = (LEVEL_1_TEST,)
    answer: GradingAnswer = unanswered
    load_error: UserError | None = None
    suite_load_error: UserError | None = None
    stopped_early: str | None = None
    suites: list[SuiteJob] = field(default_factory=list[SuiteJob])
    requests: list[RunRequest] = field(default_factory=list[RunRequest])

    @property
    def gradings(self) -> list[RunJob]:
        return [job for request in self.requests for job in request.jobs]

    def run_suite(
        self, launch: RunnerLaunch, job: SuiteJob, listener: SuiteListener | None = None
    ) -> SuiteReport:
        self.suites.append(job)
        if listener is not None and self.suite_load_error is None:
            for test in self.tests:
                listener.test_started(test.test_id)
                listener.test_finished(test)
        return SuiteReport(
            PROJECT_RUNNER,
            self.tests,
            load_error=self.suite_load_error,
            stopped_early=self.stopped_early,
        )

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        self.requests.append(request)
        jobs = tuple(self._job(job, listener) for job in request.jobs)
        return RunReport(PROJECT_RUNNER, jobs)

    def _job(self, job: RunJob, listener: CaseListener | None) -> JobReport:
        if self.load_error is not None:
            return JobReport(job.job_id, load_error=self.load_error)
        reports: list[CaseReport] = []
        for case in job.cases:
            report = CaseReport(case.id, self.answer(job, case))
            if listener is not None:
                listener.case_started(job.job_id, case.id)
                listener.case_finished(job.job_id, report)
            reports.append(report)
        return JobReport(job.job_id, tuple(reports))


@dataclass
class ScriptedBuilds:
    """What `cstudy verify` runs: D1's copy of the starter and a reference, each with a script of
    its own; a job runs the script of the build it launches in."""

    starter: ScriptedProjectProcess
    reference: ScriptedProjectProcess

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        return self._script(launch).run(launch, request, listener)

    def run_suite(
        self, launch: RunnerLaunch, job: SuiteJob, listener: SuiteListener | None = None
    ) -> SuiteReport:
        return self._script(launch).run_suite(launch, job, listener)

    def _script(self, launch: RunnerLaunch) -> ScriptedProjectProcess:
        in_the_starters_build = STARTER_BUILDS in launch.cwd.as_posix()
        return self.starter if in_the_starters_build else self.reference


def scripted_builds(*problems: Problem, passing: Sequence[str] = ()) -> ScriptedBuilds:
    """A starter whose every call raises and a reference that answers every case of `problems`
    correctly; both builds run the `passing` tests."""
    tests = tuple(SuiteTest(test_id, Passed(1_000)) for test_id in passing)
    return ScriptedBuilds(
        starter=ScriptedProjectProcess(tests, raises_not_implemented),
        reference=ScriptedProjectProcess(tests, expected_answers(*problems)),
    )


def project_environment(
    tmp_path: Path, process: ScriptedProjectProcess, **overrides: object
) -> Environment:
    """The fixture project problem, its Python runner faked and its tests generated for real."""
    return _environment(repository_root(tmp_path, PROJECT_PROBLEMS), process, overrides)


def stress_project_environment(
    tmp_path: Path, process: ScriptedProjectProcess, **overrides: object
) -> Environment:
    """The fixture project problem with stress cases and a broken overlay
    (`TALLY_SLUG`), as `project_environment` sets up the bank project."""
    return _environment(repository_root(tmp_path, PROJECT_STRESS_PROBLEMS), process, overrides)


def _environment(
    root: Path, process: ScriptedProjectProcess, overrides: Mapping[str, object]
) -> Environment:
    toolchains = project_toolchains(PythonTestGenerator())
    parts: Mapping[str, object] = {"toolchains": toolchains, "runner_process": process}
    return make_environment(root, **{**parts, **overrides})
