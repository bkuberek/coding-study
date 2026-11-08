"""`DockerSandbox` through a scripted Docker runner: the exact commands, and what it makes of their
answers. The slow tests in `test_docker_sandbox_real.py` drive a real engine."""

import json
import os
import signal
import stat
from pathlib import Path

import pytest

from coding_study.adapters.docker_sandbox import (
    STOP_TIMEOUT_S,
    DockerSandbox,
    _remove_run_folder,
)
from coding_study.adapters.stack_guard import one_off_filters
from coding_study.application.ports import ContainerCommand, ProbeResult
from coding_study.domain.docker_engine import DockerGroup, EngineState, EngineStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    AppContainer,
    GradeSetup,
    InstallPlan,
    LeftoverStack,
    MockServerInput,
    OneShot,
    ReadyStack,
    SandboxPaths,
    SandboxUser,
    StackIdentity,
    StackKind,
    StackPlan,
    StackStartError,
    StartupBudget,
    StartupFailure,
)
from tests.sandbox_fakes import ScriptedDocker

BUDGET = StartupBudget(up_s=300, app_ready_s=5)
NAME = "cstudy-t-41-abc"
PS_RUNNING = '{"Service":"app","State":"running","ExitCode":0}\n'


class Ticking:
    """A clock that moves a second each time it is read."""

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        self.now += 1.0
        return self.now


@pytest.fixture
def paths(tmp_path: Path) -> SandboxPaths:
    project = tmp_path / "projects" / "rooms"
    project.mkdir(parents=True)
    return SandboxPaths(str(project), str(tmp_path / ".cs" / "runs" / NAME))


def plan_of(paths: SandboxPaths, **changes) -> StackPlan:
    fields = {
        "identity": StackIdentity(NAME, StackKind.TEST, "digest", "rooms", 41),
        "user": SandboxUser(501, 20),
        "paths": paths,
        "app": AppContainer("node:24@sha256:1", ("node", "s.ts"), 8000, {"PORT": "8000"}),
        **changes,
    }
    return StackPlan(**fields)


def sandbox(
    docker: ScriptedDocker,
    tmp_path: Path,
    healthy=lambda _port, _path: True,
    platform: str = "darwin",
    docker_group=lambda: DockerGroup.NOT_A_MEMBER,
) -> DockerSandbox:
    return DockerSandbox(
        docker,
        runs_directory=tmp_path / ".cs" / "runs",
        health_probe=healthy,
        monotonic=Ticking(),
        sleep=lambda _seconds: None,
        platform=platform,
        docker_group=docker_group,
    )


def never_asked() -> DockerGroup:
    raise AssertionError("the docker group was looked up")


def published(docker: ScriptedDocker, port: int = 8000, at: str = "127.0.0.1:56223") -> None:
    docker.answer(("port", "cstudy-forward", str(port)), ProbeResult(0, f"{at}\n"))


def test_state_reads_the_engine_and_compose_versions(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))
    docker.answer(("docker", "compose", "version"), ProbeResult(0, "5.6.1\n"))

    assert sandbox(docker, tmp_path).state() == EngineState(EngineStatus.RUNNING, "29.9.2", "5.6.1")


def test_state_asks_with_docker_info_only_and_never_system_df(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))

    sandbox(docker, tmp_path).state()

    assert docker.commands[0][:2] == ("docker", "info")
    assert not docker.ran("system", "df")
    assert not docker.ran("desktop", "status")


def test_a_missing_binary_is_not_installed(tmp_path):
    assert sandbox(ScriptedDocker(missing=True), tmp_path).state().status is (
        EngineStatus.NOT_INSTALLED
    )


def test_a_refused_socket_is_no_permission(tmp_path):
    docker = ScriptedDocker()
    docker.answer(
        ("docker", "info"),
        ProbeResult(1, "permission denied while trying to connect to the Docker daemon socket"),
    )

    assert sandbox(docker, tmp_path).state().status is EngineStatus.NO_PERMISSION


@pytest.mark.parametrize("group", list(DockerGroup))
def test_a_refused_socket_says_where_you_stand_with_the_docker_group(tmp_path, group):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(1, "permission denied while trying to connect"))

    state = sandbox(docker, tmp_path, platform="linux", docker_group=lambda: group).state()

    assert state == EngineState(EngineStatus.NO_PERMISSION, docker_group=group)


def test_an_engine_that_answers_or_is_stopped_looks_up_no_group(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(1, "Cannot connect to the Docker daemon"))
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))
    engine = sandbox(docker, tmp_path, platform="linux", docker_group=never_asked)

    assert engine.state() == EngineState(EngineStatus.STOPPED)
    assert engine.state().running


def test_an_engine_that_does_not_answer_is_stopped(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(1, "Cannot connect to the Docker daemon"))

    assert sandbox(docker, tmp_path).state().status is EngineStatus.STOPPED


def test_a_failing_compose_is_no_compose(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))
    docker.answer(("docker", "compose", "version"), ProbeResult(1, "not a docker command"))

    assert sandbox(docker, tmp_path).state().status is EngineStatus.NO_COMPOSE


def test_start_engine_uses_docker_desktop_on_a_mac(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))

    sandbox(docker, tmp_path).start_engine(lambda _line: None)

    assert docker.commands[0] == ("docker", "desktop", "start", "--detach")


def test_start_engine_falls_back_to_opening_the_app_on_a_mac(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "desktop", "start"), ProbeResult(1, "unknown command"))
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))

    sandbox(docker, tmp_path).start_engine(lambda _line: None)

    assert docker.commands[1] == ("open", "-a", "Docker")


def test_start_engine_tries_the_user_service_on_linux(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "desktop", "start"), ProbeResult(1, "unknown command"))
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))

    sandbox(docker, tmp_path, platform="linux").start_engine(lambda _line: None)

    assert docker.commands[1] == ("systemctl", "--user", "start", "docker-desktop")


def test_start_engine_on_a_system_engine_prints_the_sudo_command_and_never_runs_it(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "desktop", "start"), ProbeResult(1, "unknown command"))
    docker.answer(("systemctl",), ProbeResult(1, "Unit docker-desktop.service not found"))

    with pytest.raises(SandboxError, match="sudo systemctl start docker"):
        sandbox(docker, tmp_path, platform="linux").start_engine(lambda _line: None)

    assert not docker.ran("sudo")


def test_start_engine_says_it_is_starting(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))
    lines: list[str] = []

    sandbox(docker, tmp_path).start_engine(lines.append)

    assert lines[0] == "starting Docker ..."


def test_start_engine_waits_until_docker_info_answers(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "info"), ProbeResult(1, "Cannot connect"))
    docker.answer(("docker", "info"), ProbeResult(1, "Cannot connect"))
    docker.answer(("docker", "info"), ProbeResult(0, "29.9.2\n"))

    sandbox(docker, tmp_path).start_engine(lambda _line: None)

    assert len(docker.ran("docker", "info")) == 3


def test_start_engine_gives_up_with_a_clear_message(tmp_path):
    docker = ScriptedDocker()
    for _ in range(200):
        docker.answer(("docker", "info"), ProbeResult(1, "Cannot connect"))

    with pytest.raises(SandboxError, match="did not answer within 120 s"):
        sandbox(docker, tmp_path).start_engine(lambda _line: None)


def test_nothing_ever_stops_the_engine(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)

    engine = sandbox(docker, tmp_path)
    plan = plan_of(paths)
    engine.start(plan, BUDGET)
    engine.stop(plan)

    assert not docker.ran("desktop", "stop")
    assert not docker.ran("systemctl", "stop")


def test_an_image_inspect_that_succeeds_means_present(tmp_path):
    docker = ScriptedDocker()

    assert sandbox(docker, tmp_path).image_present("node:24@sha256:1")
    assert docker.commands == [
        ("docker", "image", "inspect", "--format", "{{.Id}}", "node:24@sha256:1")
    ]


def test_an_image_inspect_that_fails_means_missing(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "image", "inspect"), ProbeResult(1, "No such image"))

    assert not sandbox(docker, tmp_path).image_present("node:24@sha256:1")


def test_pull_streams_its_progress(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "pull"), ProbeResult(0, "layer 1\nlayer 2\n"))
    lines: list[str] = []

    sandbox(docker, tmp_path).pull("node:24@sha256:1", lines.append)

    assert lines == ["layer 1", "layer 2"]


def test_a_failed_pull_says_so(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("docker", "pull"), ProbeResult(1, "dial tcp: lookup registry: no such host"))

    with pytest.raises(SandboxError, match="could not pull node:24"):
        sandbox(docker, tmp_path).pull("node:24@sha256:1", lambda _line: None)


def test_start_writes_the_stack_file_with_no_interpolation(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)
    plan = plan_of(paths, app=AppContainer("i@sha256:1", ("sh", "$X"), 8000, {}))

    sandbox(docker, tmp_path).start(plan, BUDGET)

    text = Path(paths.in_run("stack.yaml")).read_text(encoding="utf-8")
    assert json.loads(text)["name"] == NAME
    assert '"$$X"' in text


def test_start_writes_a_one_line_passwd_every_container_user_can_read(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)

    sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    file = Path(paths.in_run("passwd"))
    assert file.read_text(encoding="utf-8") == "cstudy:x:501:20:cstudy:/tmp/home:/bin/sh\n"
    assert stat.S_IMODE(file.stat().st_mode) == 0o644


def test_start_copies_the_forwarder_under_the_run_folder(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)

    sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    copied = Path(paths.in_run("forward.py"))
    assert "asyncio" in copied.read_text(encoding="utf-8")
    assert stat.S_IMODE(copied.stat().st_mode) == 0o644


def test_start_writes_the_rendered_mock_config_with_mock_servers(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)
    published(docker, 9000, "127.0.0.1:56224")
    mocks = MockServerInput(("room-vendor",), "secret", '{"a": 1}')

    sandbox(docker, tmp_path).start(plan_of(paths, mocks=mocks), BUDGET)

    assert Path(paths.in_run("mocks.json")).read_text(encoding="utf-8") == '{"a": 1}'


def test_start_makes_the_devcontainer_folder_for_its_read_only_mount(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)

    sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert Path(paths.devcontainer).is_dir()


def test_start_refuses_a_devcontainer_link_rather_than_mount_what_it_names(tmp_path, paths):
    outside = tmp_path / "outside"
    outside.mkdir()
    Path(paths.devcontainer).symlink_to(outside, target_is_directory=True)
    docker = ScriptedDocker()

    with pytest.raises(SandboxError, match="symbolic link"):
        sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert not docker.ran("up")


def test_start_refuses_a_grading_link_rather_than_mount_what_it_names(tmp_path, paths):
    outside = tmp_path / "outside"
    outside.mkdir()
    grading = tmp_path / "grading"
    grading.symlink_to(outside, target_is_directory=True)
    setup = GradeSetup(("true",), str(grading), 1)
    docker = ScriptedDocker()

    with pytest.raises(SandboxError, match="symbolic link"):
        sandbox(docker, tmp_path).start(plan_of(paths, grade_setup=setup), BUDGET)

    assert not docker.ran("up")


def test_start_mounts_a_grading_folder_that_is_a_folder(tmp_path, paths):
    grading = tmp_path / "grading"
    grading.mkdir()
    docker = ScriptedDocker()
    published(docker)

    sandbox(docker, tmp_path).start(
        plan_of(paths, grade_setup=GradeSetup(("true",), str(grading), 1)), BUDGET
    )

    assert docker.ran("up")


def test_start_clears_a_setuid_bit_left_in_the_project(tmp_path, paths):
    file = Path(paths.project) / "tool"
    file.write_text("x")
    file.chmod(0o4755)
    docker = ScriptedDocker()
    published(docker)

    sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert stat.S_IMODE(file.stat().st_mode) == 0o755


def test_clearing_setuid_bits_never_follows_a_link(tmp_path, paths):
    outside = tmp_path / "outside-file"
    outside.write_text("x")
    outside.chmod(0o4755)
    (Path(paths.project) / "link").symlink_to(outside)
    docker = ScriptedDocker()
    published(docker)

    sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert stat.S_IMODE(outside.stat().st_mode) == 0o4755


def test_start_brings_the_stack_up_and_waits_within_the_budget(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)

    sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    up = docker.ran("up", "--wait")[0]
    stack_file = paths.in_run("stack.yaml")
    assert up[:6] == ("docker", "compose", "--ansi", "never", "-p", NAME)
    assert ("-f", stack_file) == up[6:8]
    assert "--wait-timeout" in up
    assert up[up.index("--wait-timeout") + 1] == "300"
    assert up[up.index("--pull") + 1] == "never"
    assert "-y" not in up


def test_the_port_is_read_back_from_compose(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker, at="127.0.0.1:61001")

    ready = sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert ready.app_port == 61001
    assert ready.app_url == "http://127.0.0.1:61001"


def test_a_port_of_zero_is_a_failure_though_compose_exits_0(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker, at=":0")

    with pytest.raises(StackStartError, match="published no port") as caught:
        sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert caught.value.failure is StartupFailure.SERVICE


def test_a_port_published_beyond_loopback_is_a_failure(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker, at="0.0.0.0:61001")

    with pytest.raises(StackStartError, match="published no port"):
        sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)


def test_ready_has_a_control_port_with_mock_servers(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)
    published(docker, 9000, "127.0.0.1:56224")
    mocks = MockServerInput(("room-vendor",), "secret", "{}")

    ready = sandbox(docker, tmp_path).start(plan_of(paths, mocks=mocks), BUDGET)

    assert ready.control_port == 56224
    assert ready.control_url == "http://127.0.0.1:56224"


def test_ready_has_no_control_port_without_mock_servers(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)

    assert sandbox(docker, tmp_path).start(plan_of(paths), BUDGET).control_port is None


def test_ready_comes_only_after_the_health_path_answered(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)
    answers = iter([False, False, True])
    probes: list[tuple[int, str]] = []

    def healthy(port: int, path: str) -> bool:
        probes.append((port, path))
        return next(answers)

    ready = sandbox(docker, tmp_path, healthy).start(plan_of(paths), BUDGET)

    assert probes == [(56223, "/health")] * 3
    assert ready.ready_at > ready.started_at


def test_ready_marks_the_moment_after_the_startup(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)

    ready = sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert ready.startup_seconds == ready.ready_at - ready.started_at
    assert ready.startup_seconds > 0


def test_an_idle_app_is_ready_without_a_health_answer(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)
    idle = AppContainer("i@sha256:1", None, 8000, {})

    def never(_port: int, _path: str) -> bool:
        raise AssertionError("asked the health path of an idle app")

    assert sandbox(docker, tmp_path, never).start(plan_of(paths, app=idle), BUDGET)


def test_the_health_wait_stops_at_its_budget_with_its_own_message(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)
    docker.answer(("ps",), ProbeResult(0, PS_RUNNING))

    with pytest.raises(StackStartError) as caught:
        sandbox(docker, tmp_path, lambda _p, _h: False).start(plan_of(paths), BUDGET)

    message = str(caught.value)
    assert caught.value.failure is StartupFailure.HEALTH_TIMEOUT
    assert "/health" in message
    assert "within 5 s" in message
    assert "0.0.0.0" in message
    assert "PORT" in message


def test_an_app_that_exits_while_waiting_for_health_fails_at_once(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)
    docker.answer(("ps",), ProbeResult(0, '{"Service":"app","State":"exited","ExitCode":3}\n'))
    docker.answer(("logs",), ProbeResult(0, "Error: boom\n"))

    with pytest.raises(StackStartError) as caught:
        sandbox(docker, tmp_path, lambda _p, _h: False).start(plan_of(paths), BUDGET)

    assert caught.value.failure is StartupFailure.APP_EXITED
    assert "exited with code 3" in str(caught.value)
    assert caught.value.output == "Error: boom\n"


def test_a_failed_up_with_a_crashed_app_blames_the_app(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("up",), ProbeResult(1, "container app exited (3)"))
    docker.answer(("ps",), ProbeResult(0, '{"Service":"app","State":"exited","ExitCode":3}\n'))
    docker.answer(("logs",), ProbeResult(0, "boom\n"))

    with pytest.raises(StackStartError) as caught:
        sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert caught.value.failure is StartupFailure.APP_EXITED
    assert caught.value.output == "boom\n"


def test_a_failed_up_with_a_failed_bootstrap_blames_the_bootstrap(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("up",), ProbeResult(1, "service bootstrap didn't complete successfully"))
    docker.answer(
        ("ps",),
        ProbeResult(
            0,
            '{"Service":"bootstrap","State":"exited","ExitCode":1}\n'
            '{"Service":"app","State":"created","ExitCode":0}\n',
        ),
    )
    docker.answer(("logs",), ProbeResult(0, "migration failed\n"))
    plan = plan_of(paths, bootstrap=OneShot(("node", "m.ts")))

    with pytest.raises(StackStartError) as caught:
        sandbox(docker, tmp_path).start(plan, BUDGET)

    assert caught.value.failure is StartupFailure.BOOTSTRAP
    assert docker.ran("logs")[0][-1] == "bootstrap"
    assert caught.value.output == "migration failed\n"


def test_a_failed_up_for_any_other_reason_is_a_service_failure(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("up",), ProbeResult(1, "mounts denied: /opt/x"))
    docker.answer(("ps",), ProbeResult(0, PS_RUNNING))

    with pytest.raises(StackStartError, match="mounts denied") as caught:
        sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert caught.value.failure is StartupFailure.SERVICE


def test_a_startup_failure_says_it_is_not_a_result(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("up",), ProbeResult(1, "application not healthy after 300s"))
    docker.answer(("ps",), ProbeResult(0, PS_RUNNING))

    with pytest.raises(StackStartError, match="startup budget of 300 s") as caught:
        sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert "says nothing about your code" in str(caught.value)


def test_ps_output_as_one_array_also_reads(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("up",), ProbeResult(1, "exited"))
    docker.answer(("ps",), ProbeResult(0, '[{"Service":"app","State":"exited","ExitCode":3}]'))

    with pytest.raises(StackStartError) as caught:
        sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert caught.value.failure is StartupFailure.APP_EXITED


def test_stop_downs_a_test_stack_with_its_volumes(tmp_path, paths):
    docker = ScriptedDocker()

    assert sandbox(docker, tmp_path).stop(plan_of(paths)) is None

    assert docker.commands[-1][-4:] == ("-p", NAME, "down", "-v")
    assert docker.timeouts[-1] == STOP_TIMEOUT_S


def test_stop_keeps_a_dev_stacks_volume(tmp_path, paths):
    docker = ScriptedDocker()
    plan = plan_of(paths, identity=StackIdentity("cstudy-d-r-x", StackKind.DEV, "d", "r", 41))

    sandbox(docker, tmp_path).stop(plan)

    assert docker.commands[-1][-1] == "down"


def test_stop_removes_the_run_folder(tmp_path, paths):
    Path(paths.run).mkdir(parents=True)
    (Path(paths.run) / "stack.yaml").write_text("{}")

    sandbox(ScriptedDocker(), tmp_path).stop(plan_of(paths))

    assert not Path(paths.run).exists()


def test_stop_clears_setuid_bits_made_during_the_run(tmp_path, paths):
    file = Path(paths.project) / "tool"
    file.write_text("x")
    file.chmod(0o4755)

    sandbox(ScriptedDocker(), tmp_path).stop(plan_of(paths))

    assert stat.S_IMODE(file.stat().st_mode) == 0o755


def test_a_failed_down_is_reported_and_keeps_the_run_folder(tmp_path, paths):
    Path(paths.run).mkdir(parents=True)
    docker = ScriptedDocker()
    docker.answer(("down",), ProbeResult(1, "cannot stop"))

    problem = sandbox(docker, tmp_path).stop(plan_of(paths))

    assert problem is not None
    assert NAME in problem
    assert Path(paths.run).exists()


def test_a_test_command_runs_by_exec_in_the_app_with_its_limit(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("exec",), ProbeResult(0, "ok\n"))
    command = ContainerCommand(("node", "--test"), {"K": "v"}, 120)

    outcome = sandbox(docker, tmp_path).exec_app(plan_of(paths), command)

    call = docker.ran("exec")[0]
    assert call[call.index("exec") :] == ("exec", "-T", "-e", "K=v", "app", "node", "--test")
    assert docker.timeouts[0] == 120
    assert outcome.exit_code == 0
    assert outcome.output == "ok\n"


def test_output_is_streamed_while_a_command_runs(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("exec",), ProbeResult(0, "one\ntwo\n"))
    lines: list[str] = []

    sandbox(docker, tmp_path).exec_app(
        plan_of(paths), ContainerCommand(("x",), {}, 120, lines.append)
    )

    assert lines == ["one", "two"]


def test_a_command_past_its_limit_is_reported_as_timed_out(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("exec",), ProbeResult(124, "timed out"))

    outcome = sandbox(docker, tmp_path).exec_app(plan_of(paths), ContainerCommand(("x",), {}, 1))

    assert outcome.timed_out


def test_a_one_off_runs_with_no_dependencies_and_no_pull(tmp_path, paths):
    docker = ScriptedDocker()

    sandbox(docker, tmp_path).run_one_off(
        plan_of(paths), ContainerCommand(("reset",), {"CSTUDY_RESET_PHASE": "apply"}, 30)
    )

    call = docker.ran("run")[0]
    assert call[call.index("run") :] == (
        *("run", "--rm", "-T", "--no-deps", "--pull", "never"),
        *("-e", "CSTUDY_RESET_PHASE=apply", "app", "reset"),
    )


def install_plan_of(paths: SandboxPaths) -> InstallPlan:
    return InstallPlan(
        identity=StackIdentity("cstudy-i-rooms-d", StackKind.INSTALL, "d", "rooms", 41),
        user=SandboxUser(501, 20),
        paths=paths,
        image="node:24@sha256:1",
        command=("corepack", "pnpm", "install"),
        environment={"CI": "true"},
    )


def test_install_runs_its_one_off_with_its_limit(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("run",), ProbeResult(0, "done\n"))

    outcome = sandbox(docker, tmp_path).install(install_plan_of(paths), 600, None)

    call = docker.ran("run")[0]
    assert call[call.index("run") :] == ("run", "--rm", "-T", "--pull", "never", "install")
    assert docker.timeouts[0] == 600
    assert outcome.exit_code == 0


def test_stop_install_keeps_the_cache(tmp_path, paths):
    docker = ScriptedDocker()

    sandbox(docker, tmp_path).stop_install(install_plan_of(paths))

    assert docker.commands[-1][-1] == "down"


def test_the_inventory_asks_for_labelled_things_only(tmp_path):
    docker = ScriptedDocker()

    sandbox(docker, tmp_path).inventory()

    assert all("label=cstudy.kind" in command for command in docker.commands)
    assert len(docker.commands) == 3


def test_the_inventory_reads_containers_networks_and_volumes(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("ps",), ProbeResult(0, "cstudy-t-41-abc\ttest\tdigest\t41\n"))
    docker.answer(("network",), ProbeResult(0, "cstudy-t-41-abc_edge\tcstudy-t-41-abc\ttest\td\n"))
    docker.answer(("volume",), ProbeResult(0, "cstudy-t-41-abc_data\tcstudy-t-41-abc\ttest\td\n"))

    inventory = sandbox(docker, tmp_path).inventory()

    assert inventory.containers[0].owner_pid == 41
    assert inventory.containers[0].stack == "cstudy-t-41-abc"
    assert inventory.networks[0].name == "cstudy-t-41-abc_edge"
    assert inventory.volumes[0].stack == "cstudy-t-41-abc"


def test_an_unreadable_owner_label_reads_as_no_owner(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("ps",), ProbeResult(0, "cstudy-t-41-abc\ttest\tdigest\t\n"))

    assert sandbox(docker, tmp_path).inventory().containers[0].owner_pid is None


def test_an_inventory_that_fails_says_so(tmp_path):
    docker = ScriptedDocker()
    docker.answer(("ps",), ProbeResult(1, "Cannot connect"))

    with pytest.raises(SandboxError, match="could not list"):
        sandbox(docker, tmp_path).inventory()


def test_removing_a_leftover_stack_goes_by_project_with_no_file(tmp_path):
    docker = ScriptedDocker()

    removed = sandbox(docker, tmp_path).remove_stack(LeftoverStack(NAME, "d", removes_volumes=True))

    assert removed
    assert docker.commands[-1] == ("docker", "compose", "--ansi", "never", "-p", NAME, "down", "-v")


def test_removing_a_dev_leftover_keeps_its_volume(tmp_path):
    docker = ScriptedDocker()

    sandbox(docker, tmp_path).remove_stack(
        LeftoverStack("cstudy-d-r-x", "d", removes_volumes=False)
    )

    assert docker.commands[-1][-1] == "down"


def test_a_down_removes_the_stacks_one_offs_first(tmp_path, paths):
    """`down` leaves a one-off whose client died, running, with its network still in use, and exits
    0: a killed client would otherwise leave them for good."""
    docker = ScriptedDocker()
    docker.answer(("docker", "ps"), ProbeResult(0, "abc123\ndef456\n"))

    sandbox(docker, tmp_path).stop(plan_of(paths))

    assert docker.commands[:2] == [
        ("docker", "ps", "-aq", *one_off_filters(NAME)),
        ("docker", "rm", "-f", "-v", "abc123", "def456"),
    ]
    assert docker.commands[2][-2:] == ("down", "-v")


def test_a_stack_with_no_one_off_removes_none(tmp_path, paths):
    docker = ScriptedDocker()

    sandbox(docker, tmp_path).stop(plan_of(paths))

    assert not docker.ran("docker", "rm")


def test_a_one_off_past_its_limit_is_removed_at_once(tmp_path, paths):
    """The client is gone and the container is not: it would go on writing to the data of the case
    after it."""
    docker = ScriptedDocker()
    docker.answer(("run",), ProbeResult(124, "hung"))
    docker.answer(("docker", "ps"), ProbeResult(0, "abc123\n"))

    outcome = sandbox(docker, tmp_path).run_one_off(
        plan_of(paths), ContainerCommand(("sleep", "600"), {}, 5)
    )

    assert outcome.timed_out
    assert docker.ran("docker", "rm", "-f", "-v", "abc123")


def test_a_one_off_that_ended_by_itself_removes_nothing(tmp_path, paths):
    docker = ScriptedDocker()

    sandbox(docker, tmp_path).run_one_off(plan_of(paths), ContainerCommand(("true",), {}, 5))

    assert not docker.ran("docker", "ps")


def test_an_install_past_its_limit_is_removed_at_once(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("run",), ProbeResult(124, "hung"))
    docker.answer(("docker", "ps"), ProbeResult(0, "abc123\n"))

    sandbox(docker, tmp_path).install(install_plan_of(paths), 600, None)

    assert docker.ran("docker", "rm", "-f", "-v", "abc123")


def test_an_egress_probe_past_its_limit_is_removed_at_once(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("run",), ProbeResult(124, "hung"))
    docker.answer(("docker", "ps"), ProbeResult(0, "abc123\n"))

    sandbox(docker, tmp_path).probe_egress(plan_of(paths))

    assert docker.ran("docker", "rm", "-f", "-v", "abc123")


def test_a_command_in_the_running_app_past_its_limit_stays_for_the_stacks_down(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("exec",), ProbeResult(124, "hung"))

    sandbox(docker, tmp_path).exec_app(plan_of(paths), ContainerCommand(("sleep", "600"), {}, 5))

    assert not docker.ran("docker", "ps")


def test_removing_a_leftover_removes_its_run_folder(tmp_path):
    run = tmp_path / ".cs" / "runs" / NAME
    run.mkdir(parents=True)

    sandbox(ScriptedDocker(), tmp_path).remove_stack(LeftoverStack(NAME, "d", removes_volumes=True))

    assert not run.exists()


def test_strays_are_removed_by_name(tmp_path):
    docker = ScriptedDocker()
    engine = sandbox(docker, tmp_path)

    assert engine.remove_network(f"{NAME}_sandbox")
    assert engine.remove_volume(f"{NAME}_data")

    assert docker.commands == [
        ("docker", "network", "rm", f"{NAME}_sandbox"),
        ("docker", "volume", "rm", f"{NAME}_data"),
    ]


@pytest.mark.parametrize("label", ["../../../victim", "/tmp/victim", "", "other-project"])
def test_a_stack_name_cstudy_did_not_generate_reaches_no_command(tmp_path, label):
    docker = ScriptedDocker()

    removed = sandbox(docker, tmp_path).remove_stack(
        LeftoverStack(label, "d", removes_volumes=True)
    )

    assert not removed
    assert docker.commands == []


def test_a_stack_name_that_climbs_out_of_the_runs_folder_removes_nothing(tmp_path):
    victim = tmp_path / "victim"
    victim.mkdir()
    (tmp_path / ".cs" / "runs").mkdir(parents=True)

    sandbox(ScriptedDocker(), tmp_path).remove_stack(
        LeftoverStack("../../victim", "d", removes_volumes=True)
    )

    assert victim.is_dir()


def test_an_absolute_stack_name_removes_nothing(tmp_path):
    victim = tmp_path / "victim"
    victim.mkdir()

    sandbox(ScriptedDocker(), tmp_path).remove_stack(
        LeftoverStack(str(victim), "d", removes_volumes=True)
    )

    assert victim.is_dir()


def test_a_run_folder_is_only_ever_removed_under_the_runs_folder(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()

    _remove_run_folder(runs, "../victim")

    assert victim.is_dir()


def test_a_link_in_the_runs_folder_is_removed_and_not_followed(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "kept").write_text("x")
    (runs / NAME).symlink_to(victim)

    _remove_run_folder(runs, NAME)

    assert not (runs / NAME).is_symlink()
    assert (victim / "kept").exists()


@pytest.mark.parametrize("name", ["../x", "/tmp/x", "", "important-network", "-f"])
def test_a_network_of_another_name_is_never_removed(tmp_path, name):
    docker = ScriptedDocker()

    assert not sandbox(docker, tmp_path).remove_network(name)
    assert docker.commands == []


@pytest.mark.parametrize("name", ["../x", "/tmp/x", "", "important-volume", "-f"])
def test_a_volume_of_another_name_is_never_removed(tmp_path, name):
    docker = ScriptedDocker()

    assert not sandbox(docker, tmp_path).remove_volume(name)
    assert docker.commands == []


def test_nothing_is_ever_pruned(tmp_path, paths):
    docker = ScriptedDocker()
    engine = sandbox(docker, tmp_path)
    engine.inventory()
    engine.remove_stack(LeftoverStack(NAME, "d", removes_volumes=True))

    assert not docker.ran("prune")
    assert not any("prune" in word for command in docker.commands for word in command)


def test_a_live_owner_is_alive():
    engine = DockerSandbox(ScriptedDocker())

    assert engine.is_alive(os.getpid())


def test_the_platform_is_the_given_one(tmp_path):
    assert sandbox(ScriptedDocker(), tmp_path, platform="linux").platform() == "linux"


def running_ready() -> ReadyStack:
    return ReadyStack(NAME, 56223, None, 10.0, 12.0)


def test_restarting_the_app_stops_and_starts_only_the_app(tmp_path, paths):
    docker = ScriptedDocker()

    sandbox(docker, tmp_path).restart_app(plan_of(paths), running_ready(), BUDGET)

    assert docker.ran("stop", "app")
    assert docker.ran("up", "--detach", "--no-deps", "--no-recreate")
    assert not docker.ran("start", "app")


def test_a_restart_waits_for_the_health_path_again(tmp_path, paths):
    answers = iter([False, True])

    sandbox(ScriptedDocker(), tmp_path, healthy=lambda _port, _path: next(answers)).restart_app(
        plan_of(paths), running_ready(), BUDGET
    )

    assert next(answers, "spent") == "spent"


def test_a_start_that_fails_is_a_startup_failure_not_your_code(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("up", "--detach"), ProbeResult(1, "no such service"))

    with pytest.raises(StackStartError, match="no such service") as raised:
        sandbox(docker, tmp_path).start_app(plan_of(paths), running_ready(), BUDGET)

    assert not raised.value.failure.is_your_code


def test_an_app_that_runs_has_no_exit(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("ps", "-a", "--format", "json"), ProbeResult(0, PS_RUNNING))

    assert sandbox(docker, tmp_path).app_exit(plan_of(paths), 0) is None


def test_an_app_that_ended_gives_its_code_and_its_last_lines(tmp_path, paths):
    docker = ScriptedDocker()
    exited = '{"Service":"app","State":"exited","ExitCode":3}\n'
    docker.answer(("ps", "-a", "--format", "json"), ProbeResult(0, exited))
    docker.answer(("logs",), ProbeResult(0, "boom\n"))

    ended = sandbox(docker, tmp_path).app_exit(plan_of(paths), 0)

    assert ended is not None
    assert ended.exit_code == 3
    assert ended.output == "boom\n"


def test_an_app_that_ran_out_of_memory_says_the_limit(tmp_path, paths):
    docker = ScriptedDocker()
    exited = '{"Service":"app","State":"exited","ExitCode":137}\n'
    docker.answer(("ps", "-a", "--format", "json"), ProbeResult(0, exited))
    docker.answer(("ps", "-a", "-q", "app"), ProbeResult(0, "abc123\n"))
    docker.answer(("inspect",), ProbeResult(0, "true\n"))

    ended = sandbox(docker, tmp_path).app_exit(plan_of(paths), 0)

    assert ended is not None
    assert "memory limit of 512m" in ended.output


def test_waiting_for_an_exit_asks_again_until_it_shows(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("ps", "-a", "--format", "json"), ProbeResult(0, PS_RUNNING))
    exited = '{"Service":"app","State":"exited","ExitCode":1}\n'
    docker.answer(("ps", "-a", "--format", "json"), ProbeResult(0, exited))

    ended = sandbox(docker, tmp_path).app_exit(plan_of(paths), 5_000)

    assert ended is not None
    assert ended.exit_code == 1


def test_following_the_app_hears_each_line(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("ps", "-a", "-q", "app"), ProbeResult(0, "abc123\n"))
    docker.answer(("docker", "logs", "--follow", "abc123"), ProbeResult(0, "one\ntwo\n"))
    lines: list[str] = []

    sandbox(docker, tmp_path).follow_app(plan_of(paths), lines.append)

    assert lines == ["one", "two"]


def test_the_egress_probe_runs_alone_with_no_pull(tmp_path, paths):
    docker = ScriptedDocker()

    sandbox(docker, tmp_path).probe_egress(plan_of(paths))

    assert docker.ran("run", "--rm", "-T", "--no-deps", "--pull", "never")
    assert docker.ran("-e", "CSTUDY_EGRESS_HOSTS=", "cstudy-egress-probe")


def test_the_egress_probe_tries_the_gateway_of_each_of_the_stacks_networks(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("network", "ls"), ProbeResult(0, "n1\nn2\nn3\n"))
    docker.answer(
        ("network", "inspect"), ProbeResult(0, "172.26.0.1 \ninvalid IP fd00::1 \n172.25.0.1 \n")
    )

    sandbox(docker, tmp_path).probe_egress(plan_of(paths))

    assert docker.ran(
        "docker", "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={NAME}"
    )
    assert docker.ran("docker", "network", "inspect")[0][-3:] == ("n1", "n2", "n3")
    assert docker.ran("-e", "CSTUDY_EGRESS_HOSTS=172.25.0.1,172.26.0.1", "cstudy-egress-probe")


def test_the_egress_probe_runs_when_the_networks_cannot_be_listed(tmp_path, paths):
    docker = ScriptedDocker()
    docker.answer(("network", "ls"), ProbeResult(1, "cannot connect"))

    sandbox(docker, tmp_path).probe_egress(plan_of(paths))

    assert not docker.ran("network", "inspect")
    assert docker.ran("-e", "CSTUDY_EGRESS_HOSTS=", "cstudy-egress-probe")


def test_a_failing_reset_prepare_is_your_code(tmp_path, paths):
    docker = ScriptedDocker()
    failed = '{"Service":"reset-prepare","State":"exited","ExitCode":2}\n'
    docker.answer(("up",), ProbeResult(1, "dependency failed"))
    docker.answer(("ps", "-a", "--format", "json"), ProbeResult(0, failed))
    docker.answer(("logs",), ProbeResult(0, "no such table\n"))

    with pytest.raises(StackStartError) as raised:
        sandbox(docker, tmp_path).start(plan_of(paths), BUDGET)

    assert raised.value.failure.is_your_code
    assert "reset exited with code 2" in str(raised.value)
    assert raised.value.output == "no such table\n"


def test_the_copied_mock_code_is_readable_by_the_containers_user(tmp_path, paths):
    docker = ScriptedDocker()
    published(docker)
    published(docker, 9000, "127.0.0.1:56224")
    mocks = MockServerInput(("room-vendor",), "secret", "{}")

    sandbox(docker, tmp_path).start(plan_of(paths, mocks=mocks), BUDGET)

    copied = Path(paths.in_run("mock_server")) / "program.py"
    assert copied.stat().st_mode & 0o444 == 0o444


def test_a_signal_during_a_stop_is_held_off_and_restored(tmp_path, paths):
    held: list[object] = []

    class Noting(ScriptedDocker):
        def run(self, command, timeout_s=None, on_line=None):
            held.append(signal.getsignal(signal.SIGINT))
            return super().run(command, timeout_s, on_line)

    before = signal.getsignal(signal.SIGINT)

    sandbox(Noting(), tmp_path).stop(plan_of(paths))

    assert set(held) == {signal.SIG_IGN}
    assert signal.getsignal(signal.SIGINT) == before
