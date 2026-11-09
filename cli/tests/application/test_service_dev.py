"""`cstudy dev` through a fake engine: the foreground stack and what it holds."""

import fcntl
import json
import os
from typing import Any

import pytest

from coding_study.application.http_grading_ports import StackClients, StackEndpoints
from coding_study.application.service_dev import (
    DevRequest,
    DevStack,
    forget_dev_data,
    run_dev_stack,
)
from coding_study.application.service_stacks import workspace_id
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.domain.sandbox import (
    CommandOutcome,
    LeftoverStack,
    SandboxInventory,
    StackContainer,
    StackKind,
)
from tests.application.http_grading_fakes import FakeApp, FakeMockControl
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    CONFIG,
    SLUG,
    make_content,
    meta_document,
    write_mock,
    write_problem,
)

ENDED = CommandOutcome(3, "boom\n")


class Listener:
    def __init__(self) -> None:
        self.ready: list[DevStack] = []
        self.lines: list[str] = []

    def stack_ready(self, stack: DevStack) -> None:
        self.ready.append(stack)

    def app_line(self, line: str) -> None:
        self.lines.append(line)


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox(control_port=5001, app_ended=ENDED)


@pytest.fixture
def journal() -> list[str]:
    return []


@pytest.fixture
def environment(tmp_path, engine, journal):
    root = make_content(tmp_path)
    write_problem(root, meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}]))
    write_mock(root)

    def clients(_endpoints: StackEndpoints) -> StackClients:
        return StackClients(FakeApp(journal), FakeMockControl(journal))

    built = make_environment(root, sandbox=engine, stack_clients=clients)
    start_attempt(built, StartRequest(SLUG))
    return built


def run(environment, **fields: Any) -> tuple[CommandOutcome, Listener]:
    listener = Listener()
    ended = run_dev_stack(environment, DevRequest(SLUG, **fields), listener, lambda _line: None)
    return ended, listener


def test_it_runs_a_dev_stack_of_visible_scenarios(environment, engine):
    run(environment)

    plan = engine.plans[0]
    assert plan.identity.kind is StackKind.DEV
    scenarios = json.loads(plan.mocks.rendered_config)["mocks"]["room-vendor"]["scenarios"]
    assert sorted(scenarios) == ["outage"]


def test_it_says_where_the_app_answers_and_names_the_mock_servers(environment):
    _ended, listener = run(environment)

    assert listener.ready[0].app_url == "http://127.0.0.1:56223"
    assert listener.ready[0].mocks == ("room-vendor",)


def test_it_passes_on_what_the_app_prints(environment, engine):
    engine.app_lines = ("listening on 8000",)

    _ended, listener = run(environment)

    assert listener.lines == ["listening on 8000"]


def test_an_app_that_ends_ends_the_run_with_its_exit(environment):
    ended, _listener = run(environment)

    assert ended is ENDED


def test_the_stack_comes_down_when_the_app_ends(environment, engine):
    run(environment)

    assert len(engine.called("stop")) == 1


def test_ctrl_c_brings_the_stack_down(environment, engine):
    def interrupted() -> None:
        raise KeyboardInterrupt

    engine.on_follow = interrupted

    with pytest.raises(KeyboardInterrupt):
        run(environment)

    assert len(engine.called("stop")) == 1


def test_a_scenario_is_set_before_the_stack_is_announced(environment, journal):
    _ended, listener = run(environment, scenarios={"room-vendor": "outage"})

    assert journal == ["scenario room-vendor=outage"]
    assert listener.ready[0].scenarios == {"room-vendor": "outage"}


def test_a_hidden_scenario_exits_3_with_the_visible_names_and_starts_nothing(environment, engine):
    with pytest.raises(UsageError, match="outage"):
        run(environment, scenarios={"room-vendor": "rate_limited"})

    assert engine.plans == []


def test_an_unknown_mock_server_names_those_there_are(environment):
    with pytest.raises(UsageError, match="room-vendor"):
        run(environment, scenarios={"nobody": "outage"})


def test_it_refuses_another_kind_of_problem(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(make_content(tmp_path), toolchains=toolchains)
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))

    with pytest.raises(UsageError, match="service projects"):
        run_dev_stack(environment, DevRequest("two-sum"), Listener(), lambda _line: None)


def test_a_second_dev_stack_names_the_holder_and_starts_nothing(environment, engine):
    held = environment.root / ".cs" / "projects" / f"{SLUG}.dev.lock"
    held.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(held, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    name = f"cstudy-d-{SLUG}-{workspace_id(environment)}"
    engine.inventory_found = SandboxInventory((StackContainer(name, "dev", "w", 777),))
    try:
        with pytest.raises(UsageError, match="process 777"):
            run(environment)
    finally:
        os.close(descriptor)
    assert engine.plans == []


def forget(environment) -> list[str]:
    lines: list[str] = []
    forget_dev_data(environment, environment.problems.load(SLUG), lines.append)
    return lines


def test_forgetting_the_dev_data_removes_the_dev_stack_with_its_volumes(environment, engine):
    forget(environment)

    name = f"cstudy-d-{SLUG}-{workspace_id(environment)}"
    assert engine.called("remove_stack") == [LeftoverStack(name, workspace_id(environment), True)]


def test_a_running_dev_stack_keeps_its_data_and_says_so(environment, engine):
    held = environment.root / ".cs" / "projects" / f"{SLUG}.dev.lock"
    held.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(held, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    try:
        lines = forget(environment)
    finally:
        os.close(descriptor)

    assert engine.called("remove_stack") == []
    assert any("cstudy dev" in line for line in lines)
