"""`cstudy submit` and the visible cases of `cstudy test` on a service project, through a fake
engine and fake HTTP clients: what a run stores, what it opens, and its two clocks."""

import json
from typing import Any

import pytest

from coding_study.application.http_grading_ports import StackClients, StackEndpoints
from coding_study.application.service_grading import ServiceGrading, grade_service_project
from coding_study.application.service_lifecycle import ServiceTestRequest, run_service_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest, submit_project
from coding_study.domain.attempts import AttemptMode
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.http_grading import HttpResponse
from coding_study.domain.sandbox import StackKind, StackStartError, StartupFailure
from tests.application.http_grading_fakes import FakeApp, FakeMockControl
from tests.fakes import make_environment
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    CONFIG,
    SLUG,
    make_content,
    meta_document,
    write_cases,
    write_mock,
    write_problem,
)

LEVELS = [{"level": 1, "title": "One"}, {"level": 2, "title": "Two"}]
OK_BODY = {"status": 200, "body": {"ok": True}}
RIGHT = HttpResponse(200, {}, b'{"ok": true}', 5_000_000)
WRONG = HttpResponse(500, {}, b"{}", 5_000_000)


def case(case_id: str, level: int, path: str = "/a", **fields: object) -> dict[str, object]:
    return {
        "id": case_id,
        "level": level,
        "request": {"method": "GET", "path": path},
        "expected": OK_BODY,
        **fields,
    }


CASES = [
    case("v1", 1, visible=True),
    case("h1", 1),
    case("v2", 2, path="/b", visible=True),
    case("h2", 2, path="/b", mocks={"room-vendor": "rate_limited"}),
]


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox(control_port=5001)


@pytest.fixture
def app() -> FakeApp:
    return FakeApp([], answers={"/a": RIGHT, "/b": RIGHT})


@pytest.fixture
def control() -> FakeMockControl:
    return FakeMockControl([])


@pytest.fixture
def environment(tmp_path, engine, app, control):
    root = make_content(tmp_path)
    document = meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}])
    document["levels"] = LEVELS
    write_problem(root, document)
    write_mock(root)
    write_cases(root, CASES)

    def clients(_endpoints: StackEndpoints) -> StackClients:
        return StackClients(app, control)

    built = make_environment(root, sandbox=engine, stack_clients=clients)
    start_attempt(built, StartRequest(SLUG))
    return built


def submit(environment, **fields: Any):
    return submit_project(environment, SubmitRequest(SLUG, **fields), lambda _line: None)


def test_a_case_with_a_request_reaches_the_app(environment, app):
    submit(environment)

    assert app.journal[0] == "send GET /a"


def test_submit_grades_a_fresh_graded_stack_with_every_scenario(environment, engine):
    submit(environment)

    plan = engine.plans[0]
    assert plan.identity.kind is StackKind.GRADED
    rendered = json.loads(plan.mocks.rendered_config)["mocks"]["room-vendor"]["scenarios"]
    assert "rate_limited" in rendered


def test_the_stack_comes_down_after_the_grading(environment, engine):
    submit(environment)

    names = [name for name, _ in engine.calls]
    assert names[names.index("start") :] == ["start", "stop", "guard_released"]


def test_only_the_unlocked_levels_are_graded(environment, app):
    result = submit(environment)

    assert result.levels.ran_up_to == 1
    assert "send GET /b" not in app.journal


def test_passing_every_unlocked_level_opens_the_next_with_no_generated_tests(environment):
    result = submit(environment)

    assert result.opened is not None
    assert result.opened.level == 2
    assert result.opened.tests is None
    assert result.opened.methods == ()


def test_the_opened_level_rewrites_the_statement(environment):
    result = submit(environment)

    assert result.opened is not None
    assert environment.workspace.exists(result.opened.statement)


def test_a_failing_case_opens_nothing_and_is_stored(environment, app):
    app.answers["/a"] = WRONG

    result = submit(environment)

    assert result.opened is None
    assert result.judgement.count(CaseStatus.FAIL) == 2
    assert result.submission.tally.failed == 2


def test_a_hidden_scenario_is_set_only_for_its_own_case(environment, control):
    submit(environment)
    submit(environment)

    assert "scenario room-vendor=rate_limited" in control.journal


def test_the_time_reported_starts_at_ready(environment, engine):
    engine.started_at, engine.ready_at = 10.0, 73.0

    result = submit(environment)

    assert result.startup_seconds == 63.0
    assert result.duration_seconds < 1.0
    assert result.submission.duration_ms < 1000


@pytest.mark.parametrize(
    ("failure", "error_type"),
    [
        (StartupFailure.BOOTSTRAP, "MigrationFailed"),
        (StartupFailure.APP_EXITED, "AppDidNotStart"),
        (StartupFailure.HEALTH_TIMEOUT, "AppDidNotStart"),
    ],
)
def test_code_that_keeps_the_stack_from_ready_is_a_stored_load_error(
    environment, engine, failure, error_type
):
    engine.start_error = StackStartError(failure, "said why", "its output")

    result = submit(environment)

    assert result.judgement.load_error is not None
    assert result.judgement.load_error.type == error_type
    assert result.judgement.load_error.trace == "its output"
    assert result.submission.tally.errored == 2


def test_a_migration_in_a_mock_attempt_hides_its_output(environment, engine):
    engine.start_error = StackStartError(StartupFailure.BOOTSTRAP, "said why", "hidden row 7")
    grading = ServiceGrading(environment.problems.load(SLUG), 1, mode=AttemptMode.MOCK)

    error = grade_service_project(environment, grading, lambda _line: None).judgement.load_error

    assert error is not None
    assert "hidden row" not in error.trace
    assert "hidden row" not in error.message


@pytest.mark.parametrize("failure", [StartupFailure.SERVICE, StartupFailure.GRADE_SETUP])
def test_a_sandbox_failure_raises_and_stores_nothing(environment, engine, failure):
    engine.start_error = StackStartError(failure, "not your code")

    with pytest.raises(SandboxError):
        submit(environment)

    attempt = environment.progress.in_progress_attempt(SLUG, "typescript")
    assert environment.progress.submissions(attempt.id) == ()


def test_cstudy_test_runs_the_visible_cases_of_the_unlocked_levels(environment, app):
    result = run_service_tests(environment, ServiceTestRequest(SLUG), lambda _line: None)

    assert [verdict.case.id for verdict in result.cases.verdicts] == ["v1"]
    assert "send GET /b" not in app.journal


def test_cstudy_test_passes_only_when_the_visible_cases_pass(environment, app):
    app.answers["/a"] = WRONG

    result = run_service_tests(environment, ServiceTestRequest(SLUG), lambda _line: None)

    assert result.command_passed
    assert not result.passed


def test_cstudy_test_runs_commands_test_before_the_cases(environment, engine, app):
    run_service_tests(environment, ServiceTestRequest(SLUG), lambda _line: None)

    assert engine.called("exec_app")
    assert app.journal == ["send GET /a"]


def test_cstudy_test_uses_a_test_stack_and_stores_nothing(environment, engine):
    attempt = environment.progress.in_progress_attempt(SLUG, "typescript")

    run_service_tests(environment, ServiceTestRequest(SLUG), lambda _line: None)

    assert engine.plans[0].identity.kind is StackKind.TEST
    assert environment.progress.in_progress_attempt(SLUG, "typescript") == attempt
