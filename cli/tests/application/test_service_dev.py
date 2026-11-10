"""`cstudy dev` through a fake engine: the foreground stack and what it holds."""

import fcntl
import json
import os
from typing import Any
from unittest.mock import ANY

import pytest

from coding_study.application.http_grading_ports import StackClients, StackEndpoints
from coding_study.application.service_dev import (
    DevCommand,
    DevRequest,
    DevScenarios,
    DevStack,
    forget_dev_data,
    run_dev_command,
    run_dev_stack,
)
from coding_study.application.service_stacks import workspace_id
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.devcontainer import GENERATED_LINE
from coding_study.domain.docker_engine import INSTALL_REACHES
from coding_study.domain.errors import SandboxError, UsageError
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


def ready_stack(environment, **fields: Any) -> DevStack:
    _ended, listener = run(environment, **fields)
    return listener.ready[0]


def controls(environment, **fields: Any) -> DevScenarios:
    control = ready_stack(environment, **fields).control
    assert control is not None
    return control


def test_the_stack_names_each_mock_servers_visible_scenarios(environment):
    assert ready_stack(environment).visible == {"room-vendor": ("outage",)}


def test_a_running_stack_switches_a_mock_server_to_a_visible_scenario(environment, journal):
    controls(environment).switch("room-vendor", "outage")

    assert journal == ["scenario room-vendor=outage"]


def test_switching_says_what_each_mock_server_holds_now(environment):
    control = controls(environment)

    control.switch("room-vendor", "outage")

    assert control.current == {"room-vendor": "outage"}


def test_a_running_stack_refuses_a_hidden_scenario(environment, journal):
    control = controls(environment)

    with pytest.raises(UsageError, match="outage"):
        control.switch("room-vendor", "rate_limited")
    assert journal == []


def test_a_running_stack_refuses_a_mock_server_it_does_not_have(environment):
    with pytest.raises(UsageError, match="room-vendor"):
        controls(environment).switch("nobody", None)


def test_no_scenario_resets_the_mock_servers_and_keeps_the_others(environment, journal):
    control = controls(environment, scenarios={"room-vendor": "outage"})
    journal.clear()

    control.switch("room-vendor", None)

    assert (journal, control.current) == (["mocks reset"], {})


def test_no_run_keeps_the_app_container_idle(environment, engine):
    run(environment, idle=True)

    assert engine.plans[0].app.command is None


def test_no_run_says_the_app_is_not_running(environment):
    assert ready_stack(environment, idle=True).app_running is False


def test_debug_runs_the_app_under_its_debug_agent(environment, engine):
    run(environment, debug=True)

    assert engine.plans[0].app.command == ("node", "--inspect=0.0.0.0:9229", "src/server.ts")


def test_debug_publishes_the_languages_debug_port(environment, engine):
    run(environment, debug=True)

    assert engine.plans[0].published_debug_port == 9229


def test_debug_says_where_the_debugger_attaches(environment):
    assert ready_stack(environment, debug=True).debug_address == "127.0.0.1:50229"


def test_without_debug_there_is_no_debug_port(environment, engine):
    stack = ready_stack(environment)

    assert (engine.plans[0].debug_port, stack.debug_address) == (None, None)


def test_debug_with_no_run_publishes_the_port_and_runs_nothing(environment, engine):
    run(environment, idle=True, debug=True)

    assert (engine.plans[0].app.command, engine.plans[0].debug_port) == (None, 9229)


def test_debug_refuses_a_run_it_cannot_debug_and_starts_nothing(tmp_path):
    root = make_content(tmp_path)
    document = meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}])
    commands = document["project"]["commands"]  # type: ignore[index]
    commands["run"] = ["corepack", "pnpm", "start"]
    write_problem(root, document)
    write_mock(root)
    sandbox = FakeSandbox(app_ended=ENDED)
    built = make_environment(root, sandbox=sandbox)
    start_attempt(built, StartRequest(SLUG))

    with pytest.raises(UsageError, match="corepack pnpm start"):
        run(built, debug=True)
    assert sandbox.plans == []


def test_reset_data_removes_the_dev_stacks_data_before_it_starts(environment, engine):
    run(environment, reset_data=True)

    name = f"cstudy-d-{SLUG}-{workspace_id(environment)}"
    removed = LeftoverStack(name, workspace_id(environment), True)
    assert engine.calls.index(("remove_stack", removed)) < engine.calls.index(("start", ANY))


def test_without_reset_data_the_data_stays(environment, engine):
    run(environment)

    assert engine.called("remove_stack") == []


def test_reset_data_that_cannot_be_removed_starts_nothing(environment, engine):
    engine.removes_stacks = False

    with pytest.raises(SandboxError, match="data"):
        run(environment, reset_data=True)
    assert engine.plans == []


DEVCONTAINER = f"projects/{SLUG}/.devcontainer/devcontainer.json"


def devcontainer_of(environment) -> dict[str, Any]:
    text = environment.workspace.read_text(DEVCONTAINER)
    return json.loads(text.split("\n", 1)[1])


def test_it_writes_a_devcontainer_on_the_dev_stacks_image(environment, engine):
    run(environment)

    assert devcontainer_of(environment)["image"] == engine.plans[0].app.image


def test_the_devcontainer_joins_the_dev_stacks_network(environment):
    run(environment)

    network = f"--network=cstudy-d-{SLUG}-{workspace_id(environment)}_sandbox"
    assert network in devcontainer_of(environment)["runArgs"]


def test_the_devcontainer_mounts_the_project_at_its_same_path(environment, engine):
    run(environment)

    project = engine.plans[0].paths.project
    found = devcontainer_of(environment)
    assert (found["workspaceMount"], found["workspaceFolder"]) == (
        f"source={project},target={project},type=bind",
        project,
    )


def test_a_devcontainer_cstudy_wrote_is_written_again(environment):
    environment.workspace.write_text(DEVCONTAINER, f"{GENERATED_LINE}\n{{}}\n")

    run(environment)

    assert "image" in devcontainer_of(environment)


def test_a_devcontainer_that_is_a_link_is_never_written_through(environment, tmp_path):
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("mine\n")
    link = environment.workspace.absolute(DEVCONTAINER)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(elsewhere)

    run(environment)

    assert elsewhere.read_text() == "mine\n"


SEED = ("node", "scripts/seed.ts")


def exec_command(
    environment, command: DevCommand, **fields: Any
) -> tuple[CommandOutcome, list[object]]:
    notices: list[object] = []
    ran = run_dev_command(environment, DevRequest(SLUG, **fields), command, notices.append)
    return ran, notices


def test_exec_runs_the_command_in_a_one_off_app_container(environment, engine):
    exec_command(environment, DevCommand(SEED))

    assert engine.called("run_one_off")[0].command == SEED


def test_exec_keeps_the_app_idle_while_its_command_runs(environment, engine):
    exec_command(environment, DevCommand(SEED))

    assert engine.plans[0].app.command is None


def test_exec_ends_with_what_its_command_ended_with(environment, engine):
    engine.one_off_outcome = CommandOutcome(7, "seeded\n")

    ran, _notices = exec_command(environment, DevCommand(SEED))

    assert ran == CommandOutcome(7, "seeded\n")


def test_exec_brings_the_stack_down_after_its_command(environment, engine):
    exec_command(environment, DevCommand(SEED))

    assert len(engine.called("stop")) == 1


def test_exec_sets_a_scenario_before_its_command(environment, journal):
    exec_command(environment, DevCommand(SEED), scenarios={"room-vendor": "outage"})

    assert journal == ["scenario room-vendor=outage"]


def test_exec_writes_no_devcontainer(environment):
    exec_command(environment, DevCommand(SEED))

    assert not environment.workspace.exists(DEVCONTAINER)


ADD = ("corepack", "pnpm", "add", "left-pad")


def test_exec_with_network_runs_the_command_where_the_install_runs(environment, engine):
    exec_command(environment, DevCommand(ADD, network=True))

    assert engine.called("install")[0].command == ADD


def test_exec_with_network_starts_no_stack(environment, engine):
    exec_command(environment, DevCommand(ADD, network=True))

    assert engine.plans == []


def test_exec_with_network_says_what_it_can_reach(environment):
    _ran, notices = exec_command(environment, DevCommand(ADD, network=True))

    assert INSTALL_REACHES in notices


def test_exec_with_network_ends_with_what_its_command_ended_with(environment, engine):
    engine.install_outcome = CommandOutcome(1, "no such package\n")

    ran, _notices = exec_command(environment, DevCommand(ADD, network=True))

    assert ran.exit_code == 1


def test_exec_waits_for_no_dev_stack_another_process_holds(environment, engine):
    held = environment.root / ".cs" / "projects" / f"{SLUG}.dev.lock"
    held.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(held, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    try:
        with pytest.raises(UsageError, match="already running"):
            exec_command(environment, DevCommand(SEED))
    finally:
        os.close(descriptor)
    assert engine.called("run_one_off") == []


def test_a_devcontainer_without_cstudys_first_line_is_yours_and_kept(environment):
    environment.workspace.write_text(DEVCONTAINER, '{"image": "mine"}\n')

    run(environment)

    assert environment.workspace.read_text(DEVCONTAINER) == '{"image": "mine"}\n'
