"""P3's stack as the HTTP grader sees it, through a fake engine."""

import pytest

from coding_study.application.graded_stack import RunningStack, SandboxGradedStack
from coding_study.application.http_grading_ports import AppExit, StackStepError
from coding_study.domain.errors import RunnerStartError, SandboxError
from coding_study.domain.sandbox import (
    AppContainer,
    CommandOutcome,
    MockServerInput,
    ReadyStack,
    SandboxPaths,
    SandboxUser,
    StackIdentity,
    StackKind,
    StackPlan,
    StackStartError,
    StartupFailure,
)
from coding_study.domain.service_project import (
    ServiceApp,
    ServiceCommands,
    ServiceProject,
    ServiceRequires,
    ServiceTimeouts,
)
from tests.sandbox_fakes import FakeSandbox

IDENTITY = StackIdentity("cstudy-g-1-a", StackKind.GRADED, "d", "rooms", 1)
READY = ReadyStack("cstudy-g-1-a", 5000, 5001, 10.0, 12.0)
MOCKS = MockServerInput(("room-vendor",), "the-token", "{}")


def service_with(*, reset: tuple[str, ...] | None = ("reset",)) -> ServiceProject:
    return ServiceProject(
        image="i",
        commands=ServiceCommands(run=("r",), test=("t",), reset=reset),
        app=ServiceApp("PORT", 8000, "/health", ready_timeout_s=33),
        env={},
        requires=ServiceRequires(),
        timeouts=ServiceTimeouts(reset=7),
    )


def stack_of(engine: FakeSandbox, *, reset: tuple[str, ...] | None = ("reset",)):
    plan = StackPlan(
        IDENTITY,
        SandboxUser(1, 1),
        SandboxPaths("/p", "/r"),
        AppContainer("i", ("r",), 8000, {}),
        mocks=MOCKS,
    )
    return SandboxGradedStack(engine, RunningStack(plan, READY), service_with(reset=reset))


def failed_to_start() -> StackStartError:
    return StackStartError(StartupFailure.APP_EXITED, "your app exited", "its last lines")


def test_the_endpoints_are_the_published_ports_and_the_stacks_token():
    endpoints = stack_of(FakeSandbox()).endpoints

    assert endpoints.app_url == "http://127.0.0.1:5000"
    assert endpoints.control_url == "http://127.0.0.1:5001"
    assert endpoints.control_token == "the-token"
    assert endpoints.mocks == ("room-vendor",)


def test_the_endpoints_name_where_each_reached_service_answers_on_this_machine():
    ready = ReadyStack("cstudy-g-1-a", 5000, 5001, 10.0, 12.0, {"idp:8080": 5002})
    plan = StackPlan(
        IDENTITY, SandboxUser(1, 1), SandboxPaths("/p", "/r"), AppContainer("i", ("r",), 8000, {})
    )

    stack = SandboxGradedStack(FakeSandbox(), RunningStack(plan, ready), service_with())

    endpoints = stack.endpoints

    assert endpoints.reach == {"idp:8080": "http://127.0.0.1:5002"}


def test_a_stack_with_nothing_to_reach_names_nothing():
    assert stack_of(FakeSandbox()).endpoints.reach == {}


def test_the_app_is_reachable_by_its_own_origin_inside_the_stack():
    endpoints = stack_of(FakeSandbox()).endpoints

    assert endpoints.address_of("http://app:8000") == "http://127.0.0.1:5000"


def test_until_p10_no_other_origin_is_published():
    assert stack_of(FakeSandbox()).endpoints.origins == {}


def test_a_restart_waits_on_the_startup_budget_not_on_a_cases_limit():
    engine = FakeSandbox()

    stack_of(engine).restart_app()

    budget = engine.called("restart_app")[0]
    assert budget.app_ready_s == 33  # type: ignore[attr-defined]


def test_a_failed_restart_is_a_step_error_with_the_apps_output():
    engine = FakeSandbox(start_app_error=failed_to_start())

    with pytest.raises(StackStepError) as raised:
        stack_of(engine).restart_app()

    assert raised.value.output_tail == "its last lines"


def test_fresh_data_stops_the_app_resets_and_starts_it_in_that_order():
    engine = FakeSandbox()

    stack_of(engine).restart_app_with_fresh_data()

    names = [name for name, _ in engine.calls]
    assert names == ["stop_app", "run_one_off", "start_app"]


def test_fresh_data_runs_reset_with_the_apply_phase_and_its_own_limit():
    engine = FakeSandbox()

    stack_of(engine).restart_app_with_fresh_data()

    command = engine.called("run_one_off")[0]
    assert command.environment == {"CSTUDY_RESET_PHASE": "apply"}  # type: ignore[attr-defined]
    assert command.timeout_s == 7  # type: ignore[attr-defined]


def test_fresh_data_without_a_reset_command_only_restarts():
    engine = FakeSandbox()

    stack_of(engine, reset=None).restart_app_with_fresh_data()

    assert [name for name, _ in engine.calls] == ["restart_app"]


def test_a_failing_reset_is_a_step_error_and_starts_nothing():
    engine = FakeSandbox(one_off_outcome=CommandOutcome(3, "migration broke"))

    with pytest.raises(StackStepError, match="exited with 3") as raised:
        stack_of(engine).restart_app_with_fresh_data()

    assert raised.value.output_tail == "migration broke"
    assert engine.called("start_app") == []


def test_a_reset_past_its_limit_says_so():
    engine = FakeSandbox(one_off_outcome=CommandOutcome(124, "", timed_out=True))

    with pytest.raises(StackStepError, match="within 7 s"):
        stack_of(engine).restart_app_with_fresh_data()


def test_an_app_that_runs_has_no_exit():
    assert stack_of(FakeSandbox()).app_exit(2000) is None


def test_an_app_that_ended_gives_its_code_and_output():
    engine = FakeSandbox(app_ended=CommandOutcome(137, "killed"))

    assert stack_of(engine).app_exit(0) == AppExit(137, "killed")


def test_the_apps_output_is_read_from_the_engine_since_the_time_given():
    engine = FakeSandbox(app_output="printed\n")
    assert stack_of(engine).app_output(1700000000.5) == "printed\n"
    assert engine.calls[-1] == ("app_output_since", 1700000000.5)


def test_output_the_engine_cannot_read_is_a_stack_failure_not_a_verdict():
    engine = FakeSandbox(app_output_error=SandboxError("docker logs failed"))
    with pytest.raises(RunnerStartError, match="docker logs failed"):
        stack_of(engine).app_output(1.0)
