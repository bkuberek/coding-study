"""The events of `cstudy test --events` and `cstudy submit --events` on a project problem, in
the order the stream guarantees (docs/specs/cli.md#event-stream)."""

import json
from dataclasses import dataclass, replace

import pytest

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    CaseListener,
    ProgressNotice,
    ProjectScope,
    RunnerLaunch,
    SuiteListener,
)
from coding_study.application.project_events import (
    CaseGraded,
    CaseStarted,
    DiagnosticFound,
    LevelGraded,
    LevelOpened,
    OutputLine,
    ProjectEvent,
    RunCommand,
    RunStarted,
    SuiteTestReported,
    SuiteTestStarted,
    stream_project_tests,
    stream_submission,
)
from coding_study.application.project_testing import ProjectTestRequest
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest
from coding_study.domain.diagnostics import load_diagnostic
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.domain.runs import (
    CaseOutcome,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    UserError,
)
from coding_study.domain.suite_runs import Passed, SuiteJob, SuiteReport, SuiteTest
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS, PROJECT_PROBLEMS
from tests.project_fakes import (
    LEVEL_1_TEST,
    PROJECT_SLUG,
    FakeProjectRunner,
    ScriptedProjectProcess,
    project_environment,
    project_toolchains,
)

CASES = json.loads(
    (PROJECT_PROBLEMS / "0001-bank-project-python" / "tests.json").read_text(encoding="utf-8")
)["cases"]
EXPECTED = {case["id"]: case["expected"] for case in CASES}
NOTICE = "warming the project runner"
BROKEN = UserError("SyntaxError", "invalid syntax", "bank/bank.py:5")
MINE = SuiteTest("tests/test_mine.py::test_overdraft", Passed(1000))


def correct(job: RunJob, case: RunCase) -> CaseOutcome:
    return Returned(EXPECTED[case.id], 1000)


def wrong_on_h1(job: RunJob, case: RunCase) -> CaseOutcome:
    return Returned(["wrong"], 1000) if case.id == "h1" else correct(job, case)


@dataclass
class NoticingRunner(FakeProjectRunner):
    """Says what it is doing before it launches, as a runner that warms up does."""

    def prepare_project(self, scope: ProjectScope, notify: ProgressNotice) -> RunnerLaunch:
        notify(NOTICE)
        return FakeProjectRunner.prepare_project(self, scope, notify)


@dataclass
class Unheard:
    """Runs as `process` does, but tells no listener: a runner whose results come at the end."""

    process: ScriptedProjectProcess

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        return self.process.run(launch, request)

    def run_suite(
        self, launch: RunnerLaunch, job: SuiteJob, listener: SuiteListener | None = None
    ) -> SuiteReport:
        return self.process.run_suite(launch, job)


@pytest.fixture
def process() -> ScriptedProjectProcess:
    return ScriptedProjectProcess(answer=correct)


@pytest.fixture
def environment(tmp_path, process) -> Environment:
    toolchains = project_toolchains(PythonTestGenerator(), NoticingRunner())
    environment = project_environment(tmp_path, process, toolchains=toolchains)
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment


def streamed_tests(environment: Environment, **fields: object) -> list[ProjectEvent]:
    events: list[ProjectEvent] = []
    request = replace(ProjectTestRequest(), **fields)  # type: ignore[arg-type]
    stream_project_tests(environment, request, events.append)
    return events


def streamed_submission(environment: Environment, **fields: object) -> list[ProjectEvent]:
    events: list[ProjectEvent] = []
    request = replace(SubmitRequest(), **fields)  # type: ignore[arg-type]
    stream_submission(environment, request, events.append)
    return events


def kinds(events: list[ProjectEvent]) -> list[type]:
    return [type(event) for event in events]


def first_start(events: list[ProjectEvent]) -> RunStarted:
    first = events[0]
    assert isinstance(first, RunStarted)
    return first


def test_a_test_run_starts_by_naming_itself(environment):
    assert first_start(streamed_tests(environment)).command is RunCommand.TEST


def test_the_start_names_the_levels_the_run_covers(environment):
    assert first_start(streamed_tests(environment)).levels.ran_up_to == 1


def test_a_test_run_passes_notices_on_then_reports_each_test_as_it_starts_and_ends(
    environment, process
):
    process.tests = (LEVEL_1_TEST, MINE)
    assert kinds(streamed_tests(environment)) == [
        RunStarted,
        OutputLine,
        SuiteTestStarted,
        SuiteTestReported,
        SuiteTestStarted,
        SuiteTestReported,
    ]


def test_a_started_test_is_named(environment):
    assert streamed_tests(environment)[2] == SuiteTestStarted(LEVEL_1_TEST.test_id)


def test_tests_the_runner_did_not_report_live_come_when_the_suite_ends(environment, process):
    environment = replace(environment, runner_process=Unheard(process))
    assert kinds(streamed_tests(environment)) == [RunStarted, OutputLine, SuiteTestReported]


def test_a_notice_keeps_its_text(environment):
    assert streamed_tests(environment)[1] == OutputLine(NOTICE)


def test_tests_are_reported_in_run_order(environment, process):
    process.tests = (MINE, LEVEL_1_TEST)
    reported = [
        event for event in streamed_tests(environment) if isinstance(event, SuiteTestReported)
    ]
    assert [event.verdict.test.test_id for event in reported] == [
        MINE.test_id,
        LEVEL_1_TEST.test_id,
    ]


def test_diagnostics_follow_the_tests(environment, process):
    process.tests = (SuiteTest("tests/test_level_1.py", Raised(BROKEN, 0)),)
    assert kinds(streamed_tests(environment))[-2:] == [SuiteTestReported, DiagnosticFound]


def test_a_diagnostic_carries_the_load_error(environment, process):
    process.tests = (SuiteTest("tests/test_level_1.py", Raised(BROKEN, 0)),)
    assert streamed_tests(environment)[-1] == DiagnosticFound(load_diagnostic(BROKEN))


def test_a_locked_level_stops_the_run_before_any_event(environment):
    events: list[ProjectEvent] = []
    with pytest.raises(UsageError):
        stream_project_tests(environment, ProjectTestRequest(level=2), events.append)
    assert events == []


def test_a_case_that_names_no_test_fails_after_the_start(environment):
    events: list[ProjectEvent] = []
    with pytest.raises(UsageError):
        stream_project_tests(environment, ProjectTestRequest(case_ids=("nope",)), events.append)
    assert kinds(events)[0] is RunStarted


def test_a_submission_starts_by_naming_itself(environment):
    assert first_start(streamed_submission(environment)).command is RunCommand.SUBMIT


def test_a_passing_submission_grades_each_case_as_it_starts_and_ends_then_opens_a_level(
    environment,
):
    assert kinds(streamed_submission(environment)) == [
        RunStarted,
        OutputLine,
        *([CaseStarted, CaseGraded] * 3),
        LevelGraded,
        LevelOpened,
    ]


def test_a_started_case_carries_its_visibility_and_level(environment):
    started = [e for e in streamed_submission(environment) if isinstance(e, CaseStarted)]
    assert [(event.case.id, event.case.visible, event.level) for event in started] == [
        ("ex1", True, 1),
        ("h1", False, 1),
        ("h2", False, 1),
    ]


def test_cases_the_runner_did_not_report_live_come_when_the_grading_ends(environment, process):
    environment = replace(environment, runner_process=Unheard(process))
    assert kinds(streamed_submission(environment)) == [
        RunStarted,
        OutputLine,
        *([CaseGraded] * 3),
        LevelGraded,
        LevelOpened,
    ]


def test_a_graded_case_carries_its_level(environment):
    graded = [event for event in streamed_submission(environment) if isinstance(event, CaseGraded)]
    assert {event.level for event in graded} == {1}


def test_the_opened_level_is_the_next(environment):
    opened = [
        event.opened for event in streamed_submission(environment) if isinstance(event, LevelOpened)
    ]
    assert [level.level for level in opened] == [2]


def test_a_failing_submission_opens_nothing(environment, process):
    process.answer = wrong_on_h1
    assert kinds(streamed_submission(environment))[-1] is LevelGraded


def test_a_mock_attempt_names_no_hidden_case(environment, process):
    start_attempt(environment, StartRequest(PROJECT_SLUG, fresh=True, mock=True))
    process.answer = wrong_on_h1
    named = [
        event.case.id if isinstance(event, CaseStarted) else event.verdict.case.id
        for event in streamed_submission(environment)
        if isinstance(event, CaseStarted | CaseGraded)
    ]
    assert named == ["ex1", "ex1"]


def test_code_that_does_not_load_is_a_diagnostic_before_the_levels(environment, process):
    process.load_error = BROKEN
    assert kinds(streamed_submission(environment)) == [
        RunStarted,
        OutputLine,
        DiagnosticFound,
        LevelGraded,
    ]


def test_a_locked_level_stops_the_submission_before_any_event(environment):
    events: list[ProjectEvent] = []
    with pytest.raises(UsageError):
        stream_submission(environment, SubmitRequest(level=2), events.append)
    assert events == []


def test_another_kind_of_problem_stops_the_submission_before_any_event(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS), toolchains=toolchains
    )
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    events: list[ProjectEvent] = []
    with pytest.raises(UsageError, match="cstudy submit is for project problems"):
        stream_submission(environment, SubmitRequest(), events.append)
    assert events == []
