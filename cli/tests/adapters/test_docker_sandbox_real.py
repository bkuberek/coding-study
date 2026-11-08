"""A real Docker engine: the sandbox as the spike measured it, on resources this test labels and
removes. Run with `uv run pytest -q -m docker`. Waits are generous, for a busy machine; what these
tests measure is whether things happen, not how fast."""

import http.client
import ipaddress
import json
import os
import signal
import socket
import subprocess
import sys
import textwrap
import threading
import time
from collections.abc import Generator
from contextlib import suppress
from pathlib import Path

import pytest

from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
from coding_study.adapters.docker_setup import docker_group_of_this_process
from coding_study.adapters.http_grader.clients import open_stack_clients
from coding_study.application.http_grading_ports import StackEndpoints
from coding_study.application.ports import ContainerCommand
from coding_study.application.sandbox import running_stack, sweep_leftovers
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.mock_configs import MockFiles, ScenarioReach, rendered_mock_config
from coding_study.domain.sandbox import (
    EGRESS_PROBE,
    PYTHON_IMAGE,
    AppContainer,
    InstallPlan,
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
from tests.waits import GENEROUS_WAIT_S, POLL_S

pytestmark = [pytest.mark.slow, pytest.mark.docker]

BUDGET = StartupBudget(up_s=int(GENEROUS_WAIT_S), app_ready_s=int(GENEROUS_WAIT_S))
SERVER = textwrap.dedent(
    """\
    import http.server, os


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok from the app")

        def log_message(self, *arguments):
            pass


    http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), Handler).serve_forever()
    """
)
PROBE = "import json,os,socket,sys\n"
SECRET_NAME = "above-the-project.txt"
IPV4 = 4
IPV6_SUBNET = "fd00:c5d::/64"
IPV6_KIND_LABEL = "cstudy.kind=test-ipv6"


def docker(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *arguments],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=GENEROUS_WAIT_S,
        check=False,
    )


@pytest.fixture(scope="module", autouse=True)
def require_engine() -> None:
    try:
        if docker("info", "--format", "{{.ServerVersion}}").returncode != 0:
            pytest.skip("no running Docker engine")
    except FileNotFoundError:
        pytest.skip("no docker on PATH")
    if docker("image", "inspect", PYTHON_IMAGE).returncode != 0:
        pytest.skip("the pinned Python image is not here; a test pulls nothing")


@pytest.fixture
def engine(tmp_path: Path) -> DockerSandbox:
    return DockerSandbox(SubprocessDockerRunner(), runs_directory=tmp_path / "runs")


def project_in(tmp_path: Path) -> Path:
    project = tmp_path.resolve() / "workspace" / "projects" / "sample"
    project.mkdir(parents=True)
    (project / "server.py").write_text(SERVER)
    (project.parent.parent / SECRET_NAME).write_text("never seen\n")
    return project


def plan_of(tmp_path: Path, name: str, **changes: object) -> StackPlan:
    project = project_in(tmp_path)
    fields: dict[str, object] = {
        "identity": StackIdentity(name, StackKind.TEST, "testworkspace", "sample", os.getpid()),
        "user": SandboxUser(os.getuid(), os.getgid()),
        "paths": SandboxPaths(str(project), str(tmp_path.resolve() / "runs" / name)),
        "app": AppContainer(PYTHON_IMAGE, ("python", "-I", "server.py"), 8000, {"PORT": "8000"}),
        **changes,
    }
    return StackPlan(**fields)  # type: ignore[arg-type]


def stack_name(tag: str) -> str:
    return f"cstudy-t-{os.getpid()}-{tag}"


def resources_of(name: str) -> dict[str, list[str]]:
    label = f"label=com.docker.compose.project={name}"
    return {
        "containers": docker("ps", "-aq", "--filter", label).stdout.split(),
        "networks": docker("network", "ls", "-q", "--filter", label).stdout.split(),
        "volumes": docker("volume", "ls", "-q", "--filter", label).stdout.split(),
    }


def nothing_left(name: str) -> bool:
    return not any(resources_of(name).values())


def get(port: int, path: str = "/") -> tuple[int, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=GENEROUS_WAIT_S)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


@pytest.fixture
def stack(
    engine: DockerSandbox, tmp_path: Path
) -> Generator[tuple[DockerSandbox, StackPlan, ReadyStack]]:
    plan = plan_of(tmp_path, stack_name("main"))
    with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
        yield engine, plan, ready


def probe(stack: tuple[DockerSandbox, StackPlan, ReadyStack], code: str) -> dict[str, object]:
    engine, plan, _ = stack
    outcome = engine.exec_app(
        plan,
        ContainerCommand(("python", "-I", "-c", PROBE + code), {}, GENEROUS_WAIT_S),
    )
    assert outcome.exit_code == 0, outcome.output
    return json.loads(outcome.output)


@pytest.mark.skipif(os.geteuid() == 0, reason="root passes any file mode")
def test_a_socket_that_refuses_you_is_no_permission_with_your_docker_group(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
):
    refusing = tmp_path_factory.mktemp("s") / "r.sock"
    with socket.socket(socket.AF_UNIX) as bound:
        bound.bind(str(refusing))
    refusing.chmod(0)
    monkeypatch.setenv("DOCKER_HOST", f"unix://{refusing}")

    state = DockerSandbox(SubprocessDockerRunner()).state()

    assert state == EngineState(
        EngineStatus.NO_PERMISSION, docker_group=docker_group_of_this_process()
    )


def test_the_app_answers_on_its_dynamic_loopback_port(stack):
    _, _, ready = stack

    assert ready.app_url.startswith("http://127.0.0.1:")
    assert get(ready.app_port) == (200, b"ok from the app")


def test_ready_is_a_moment_after_the_start(stack):
    _, _, ready = stack

    assert ready.ready_at > ready.started_at


def test_the_port_is_on_loopback_only(stack):
    _, plan, ready = stack

    published = docker(
        "compose", "-p", plan.identity.name, "port", "cstudy-forward", "8000"
    ).stdout.strip()

    assert published == f"127.0.0.1:{ready.app_port}"


def test_the_app_container_has_no_way_out(stack):
    found = probe(
        stack,
        textwrap.dedent(
            """\
            def reach(host, port):
                try:
                    socket.create_connection((host, port), 3).close()
                    return "connected"
                except OSError as error:
                    return error.__class__.__name__ + str(error.errno)


            print(json.dumps({
                "public": reach("1.1.1.1", 443),
                "metadata": reach("169.254.169.254", 80),
                "lan": reach("192.168.1.1", 80),
                "name": reach("example.com", 443),
                "host": reach("host.docker.internal", 80),
            }))
            """
        ),
    )

    assert "connected" not in found.values()


def this_machine_on(stack: str) -> list[str]:
    """Where a bridge of the stack's networks would hold an address of this machine's: the gateway
    and the first address of each IPv4 subnet."""
    networks = resources_of(stack)["networks"]
    found = docker("network", "inspect", "--format", "{{json .IPAM.Config}}", *networks)
    addresses: set[str] = set()
    for line in found.stdout.splitlines():
        for config in json.loads(line) or []:
            subnet = ipaddress.ip_network(config["Subnet"])
            if subnet.version == IPV4:
                addresses.add(str(next(subnet.hosts())))
                with suppress(ValueError):
                    addresses.add(str(ipaddress.IPv4Address(config.get("Gateway") or "")))
    return sorted(addresses)


def test_the_app_container_cannot_reach_this_machine(stack):
    _, plan, _ = stack
    addresses = this_machine_on(plan.identity.name)

    with socket.create_server(("0.0.0.0", 0)) as listener:
        port = listener.getsockname()[1]
        found = probe(
            stack,
            textwrap.dedent(
                f"""\
                def reached(host):
                    try:
                        socket.create_connection((host, {port}), 3).close()
                        return True
                    except OSError:
                        return False


                print(json.dumps([host for host in {addresses!r} if reached(host)]))
                """
            ),
        )

    assert addresses
    assert found == []


def test_a_file_above_the_project_folder_cannot_be_seen(stack):
    _, plan, _ = stack
    parent = Path(plan.paths.project).parent.parent

    found = probe(
        stack,
        f"print(json.dumps({{'file': os.path.exists({str(parent / SECRET_NAME)!r}),"
        f" 'parent': os.listdir({str(parent)!r})}}))",
    )

    assert found["file"] is False
    assert found["parent"] == ["projects"]


def test_the_project_folder_is_at_its_own_path_and_writable(stack):
    _, plan, _ = stack

    found = probe(
        stack,
        "open('written-inside.txt','w').write('x');"
        "print(json.dumps({'cwd': os.getcwd(), 'uid': os.getuid()}))",
    )

    assert found == {"cwd": plan.paths.project, "uid": os.getuid()}
    assert (Path(plan.paths.project) / "written-inside.txt").read_text() == "x"


def test_the_docker_socket_is_not_there(stack):
    found = probe(stack, "print(json.dumps(os.path.exists('/var/run/docker.sock')))")

    assert found is False


def test_the_container_holds_no_capability_and_cannot_gain_one(stack):
    found = probe(
        stack,
        "lines=dict(l.split(':',1) for l in open('/proc/self/status') if ':' in l);"
        "print(json.dumps({'cap': lines['CapEff'].strip(), 'nnp': lines['NoNewPrivs'].strip()}))",
    )

    assert found == {"cap": "0000000000000000", "nnp": "1"}


def test_the_root_filesystem_is_read_only(stack):
    found = probe(
        stack,
        textwrap.dedent(
            """\
            try:
                open('/etc/written','w')
                print(json.dumps('written'))
            except OSError as error:
                print(json.dumps(error.strerror))
            """
        ),
    )

    assert found == "Read-only file system"


def test_the_devcontainer_folder_cannot_be_written_from_inside(stack):
    found = probe(
        stack,
        textwrap.dedent(
            """\
            try:
                open('.devcontainer/devcontainer.json','w')
                print(json.dumps('written'))
            except OSError as error:
                print(json.dumps(error.strerror))
            """
        ),
    )

    assert found == "Read-only file system"


def test_home_and_data_are_writable_as_the_user(stack):
    found = probe(
        stack,
        "open('/data/d','w').write('x');os.makedirs(os.environ['HOME'],exist_ok=True);"
        "open(os.environ['HOME']+'/h','w').write('x');print(json.dumps(os.environ['HOME']))",
    )

    assert found == "/tmp/home"


def test_the_passwd_entry_names_the_user(stack):
    found = probe(
        stack,
        "import pwd;print(json.dumps(pwd.getpwuid(os.getuid()).pw_name))",
    )

    assert found == "cstudy"


def test_only_what_the_stack_declares_reaches_its_environment(stack):
    found = probe(stack, "print(json.dumps(sorted(os.environ)))")

    assert "PORT" in found
    assert "CSTUDY_DATA_DIR" in found
    assert not [name for name in found if "TOKEN" in name or "SECRET" in name]


def test_every_kind_of_resource_carries_the_labels(stack):
    engine, plan, _ = stack

    inventory = engine.inventory()
    name = plan.identity.name

    assert [item for item in inventory.containers if item.stack == name]
    assert [item for item in inventory.networks if item.stack == name]
    assert [item for item in inventory.volumes if item.stack == name]
    assert all(item.owner_pid == os.getpid() for item in inventory.containers if item.stack == name)


CHATTY = (
    "python",
    "-I",
    "-c",
    "import sys\nfor _ in range(50 * 1024):\n    sys.stdout.write('x' * 1023 + chr(10))",
)
MEGABYTE = 1024 * 1024
KEPT_BY_THE_LIMITS = 30 * MEGABYTE
"""`max-size` times `max-file`: the most the engine keeps of one container's output."""


def test_a_chatty_one_off_keeps_no_more_log_than_its_limits(stack):
    """50 MiB of output, past the 30 MiB the limits allow; `docker logs` reads what is kept."""
    _, plan, _ = stack
    name = f"{plan.identity.name}-chatty"

    arguments = (
        *("compose", "--ansi", "never", "-p", plan.identity.name),
        *("-f", plan.paths.in_run("stack.yaml")),
        *("run", "-d", "--no-deps", "--pull", "never", "--name", name, "app", *CHATTY),
    )
    try:
        started = docker(*arguments)
        assert started.returncode == 0, started.stderr
        waited = docker("wait", name)
        assert waited.stdout.strip() == "0", waited.stderr

        kept = subprocess.run(
            ["docker", "logs", name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=GENEROUS_WAIT_S,
            check=False,
        ).stdout
        config = docker("inspect", "--format", "{{json .HostConfig.LogConfig}}", name).stdout

        assert 10 * MEGABYTE < len(kept) <= KEPT_BY_THE_LIMITS
        assert json.loads(config) == {
            "Type": "json-file",
            "Config": {"max-file": "3", "max-size": "10m"},
        }
    finally:
        docker("rm", "-f", "-v", name)


def test_a_stopped_stack_leaves_nothing(engine, tmp_path):
    name = stack_name("stops")
    plan = plan_of(tmp_path, name)

    with running_stack(engine, plan, BUDGET, lambda _line: None):
        assert resources_of(name)["containers"]

    assert nothing_left(name)
    assert not Path(plan.paths.run).exists()


def test_a_compose_setting_in_the_folder_you_ran_cstudy_in_changes_nothing(
    engine, tmp_path, monkeypatch
):
    """Without `-f`, as in every `down`, compose reads `.env` from its current folder."""
    name = stack_name("dotenv")
    plan = plan_of(tmp_path, name)
    yours = tmp_path / "yours"
    yours.mkdir()
    (yours / ".env").write_text("COMPOSE_PARALLEL_LIMIT=not-a-number\n")
    monkeypatch.chdir(yours)
    try:
        with running_stack(engine, plan, BUDGET, lambda _line: None):
            assert resources_of(name)["containers"]

        assert nothing_left(name)
    finally:
        remove_everything_of(name)


def test_a_stop_of_a_stack_takes_seconds_not_the_default_grace(engine, tmp_path):
    """`init: true` and the short grace: without them each `down` costs 10 s."""
    plan = plan_of(tmp_path, stack_name("grace"))
    engine.start(plan, BUDGET)

    began = time.monotonic()
    engine.stop(plan)

    assert time.monotonic() - began < 10.0


def test_an_app_that_crashes_is_said_with_its_output_and_the_stack_comes_down(engine, tmp_path):
    name = stack_name("crash")
    command = ("python", "-I", "-c", "import sys;print('boom in the app');sys.exit(3)")
    plan = plan_of(tmp_path, name, app=AppContainer(PYTHON_IMAGE, command, 8000, {"PORT": "8000"}))

    with (
        pytest.raises(StackStartError) as caught,
        running_stack(engine, plan, BUDGET, lambda _line: None),
    ):
        pass

    assert caught.value.failure is StartupFailure.APP_EXITED
    assert "code 3" in str(caught.value)
    assert "boom in the app" in caught.value.output
    assert nothing_left(name)


def test_an_app_that_never_answers_runs_out_of_its_budget_and_says_so(engine, tmp_path):
    name = stack_name("silent")
    idle = ("python", "-I", "-c", "import time;time.sleep(600)")
    plan = plan_of(tmp_path, name, app=AppContainer(PYTHON_IMAGE, idle, 8000, {"PORT": "8000"}))
    budget = StartupBudget(up_s=int(GENEROUS_WAIT_S), app_ready_s=3)

    with pytest.raises(StackStartError) as caught, running_stack(engine, plan, budget, print):
        pass

    assert caught.value.failure is StartupFailure.HEALTH_TIMEOUT
    assert "within 3 s" in str(caught.value)
    assert nothing_left(name)


def test_a_command_past_its_limit_is_a_timeout_from_ready(stack):
    """The limit is the second clock: it starts at ready, so `up` took none of it."""
    engine, plan, _ = stack

    outcome = engine.exec_app(
        plan, ContainerCommand(("python", "-I", "-c", "import time;time.sleep(600)"), {}, 1)
    )

    assert outcome.timed_out


def wait_until_nothing_left(name: str) -> None:
    deadline = time.monotonic() + GENEROUS_WAIT_S
    while time.monotonic() < deadline:
        if nothing_left(name):
            return
        time.sleep(POLL_S * 25)
    raise AssertionError(f"{name} is still there: {resources_of(name)}")


OWNER_PROGRAM = textwrap.dedent(
    """\
    import json, os, sys, time
    from pathlib import Path

    from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
    from coding_study.application.sandbox import running_stack
    from coding_study.domain.sandbox import (
        AppContainer, SandboxPaths, SandboxUser, StackIdentity, StackKind, StackPlan, StartupBudget,
    )

    name, image, project, run = sys.argv[1:5]
    engine = DockerSandbox(SubprocessDockerRunner(), runs_directory=Path(run).parent)
    plan = StackPlan(
        identity=StackIdentity(name, StackKind.TEST, "testworkspace", "sample", os.getpid()),
        user=SandboxUser(os.getuid(), os.getgid()),
        paths=SandboxPaths(project, run),
        app=AppContainer(image, ("python", "-I", "server.py"), 8000, {"PORT": "8000"}),
    )
    with running_stack(engine, plan, StartupBudget(300, 300), print):
        print("ready", flush=True)
        time.sleep(600)
    """
)


def owner_process(
    tmp_path: Path, name: str, program: str = OWNER_PROGRAM
) -> tuple[subprocess.Popen[str], int]:
    project = project_in(tmp_path)
    source = Path(__file__).parents[2] / "src"
    owner = subprocess.Popen(
        [
            sys.executable,
            "-c",
            program,
            name,
            PYTHON_IMAGE,
            str(project),
            str(tmp_path.resolve() / "runs" / name),
        ],
        stdout=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": str(source)},
    )
    assert owner.stdout is not None
    assert owner.stdout.readline().strip() == "ready"
    return owner, owner.pid


def test_a_killed_owner_leaves_nothing_behind(tmp_path):
    """The guard: SIGKILL to the owner, and the stack comes down with no `cstudy` left."""
    name = stack_name("killed")
    owner, pid = owner_process(tmp_path, name)
    assert resources_of(name)["containers"]

    os.kill(pid, signal.SIGKILL)
    owner.wait()

    wait_until_nothing_left(name)
    wait_until_gone(tmp_path.resolve() / "runs" / name)


HANGS = ("python", "-I", "-c", "import time;print('hung',flush=True);time.sleep(600)")
ONE_OFF_LIMIT_S = 20
"""The limit under test, long enough for the one-off to be running when it ends."""
ONE_OFF_OWNER = textwrap.dedent(
    """\
    import os, signal, sys
    from pathlib import Path

    from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
    from coding_study.application.ports import ContainerCommand
    from coding_study.application.sandbox import running_stack
    from coding_study.domain.sandbox import (
        AppContainer, SandboxPaths, SandboxUser, StackIdentity, StackKind, StackPlan, StartupBudget,
    )

    signal.signal(signal.SIGINT, signal.default_int_handler)
    name, image, project, run = sys.argv[1:5]
    engine = DockerSandbox(SubprocessDockerRunner(), runs_directory=Path(run).parent)
    plan = StackPlan(
        identity=StackIdentity(name, StackKind.TEST, "testworkspace", "sample", os.getpid()),
        user=SandboxUser(os.getuid(), os.getgid()),
        paths=SandboxPaths(project, run),
        app=AppContainer(image, ("python", "-I", "server.py"), 8000, {"PORT": "8000"}),
    )
    hangs = ("python", "-I", "-c", "import time;time.sleep(600)")
    with running_stack(engine, plan, StartupBudget(300, 300), print):
        print("ready", flush=True)
        engine.run_one_off(plan, ContainerCommand(hangs, {}, 600))
    """
)
INSTALL_OWNER = textwrap.dedent(
    """\
    import os, signal, sys
    from pathlib import Path

    from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
    from coding_study.domain.sandbox import (
        InstallPlan, SandboxPaths, SandboxUser, StackIdentity, StackKind,
    )

    signal.signal(signal.SIGINT, signal.default_int_handler)
    name, image, project, run = sys.argv[1:5]
    engine = DockerSandbox(SubprocessDockerRunner(), runs_directory=Path(run).parent)
    plan = InstallPlan(
        identity=StackIdentity(name, StackKind.INSTALL, "testworkspace", "sample", os.getpid()),
        user=SandboxUser(os.getuid(), os.getgid()),
        paths=SandboxPaths(project, run),
        image=image,
        command=("python", "-I", "-c", "import time;time.sleep(600)"),
        environment={},
    )
    with engine.guard(plan.identity):
        print("ready", flush=True)
        try:
            engine.install(plan, 600, None)
        finally:
            engine.stop_install(plan)
    """
)


def running_one_offs(name: str) -> list[str]:
    return docker(
        "ps",
        "-q",
        "--filter",
        f"label=com.docker.compose.project={name}",
        "--filter",
        "label=com.docker.compose.oneoff=True",
    ).stdout.split()


def wait_for_a_one_off(name: str) -> None:
    deadline = time.monotonic() + GENEROUS_WAIT_S
    while not running_one_offs(name):
        assert time.monotonic() < deadline, f"no one-off of {name} is running"
        time.sleep(POLL_S * 25)


def wait_until_no_container_or_network(name: str) -> None:
    deadline = time.monotonic() + GENEROUS_WAIT_S
    while time.monotonic() < deadline:
        left = resources_of(name)
        if not left["containers"] and not left["networks"]:
            return
        time.sleep(POLL_S * 25)
    raise AssertionError(f"{name} is still there: {resources_of(name)}")


def remove_everything_of(name: str) -> None:
    """What a failing test would otherwise leave on the engine; nothing when it passed."""
    left = resources_of(name)
    if left["containers"]:
        docker("rm", "-f", "-v", *left["containers"])
    for network in left["networks"]:
        docker("network", "rm", network)
    for volume in left["volumes"]:
        docker("volume", "rm", volume)


def test_a_one_off_past_its_limit_is_gone_when_the_call_returns(stack):
    engine, plan, _ = stack

    outcome = engine.run_one_off(plan, ContainerCommand(HANGS, {}, ONE_OFF_LIMIT_S))

    assert outcome.timed_out
    assert "hung" in outcome.output
    assert not running_one_offs(plan.identity.name)


def test_an_install_past_its_limit_leaves_nothing_running_and_keeps_its_cache(engine, tmp_path):
    name = f"cstudy-i-hung-{os.getpid()}"
    plan = install_plan_of(tmp_path, name, HANGS)
    try:
        with engine.guard(plan.identity):
            outcome = engine.install(plan, ONE_OFF_LIMIT_S, None)
            problem = engine.stop_install(plan)

        assert outcome.timed_out
        assert "hung" in outcome.output
        assert problem is None
        left = resources_of(name)
        assert not left["containers"]
        assert not left["networks"]
        assert left["volumes"]
    finally:
        remove_everything_of(name)


@pytest.mark.parametrize("ending", [signal.SIGINT, signal.SIGKILL], ids=["ctrl-c", "killed"])
def test_an_owner_that_ends_during_a_one_off_leaves_nothing_behind(tmp_path, ending):
    """A `reset`, a second `bootstrap` or a probe: Ctrl-C reaches `stop`, a SIGKILL the guard."""
    name = stack_name(f"oneoff-{ending.name.lower()}")
    try:
        owner, pid = owner_process(tmp_path, name, ONE_OFF_OWNER)
        wait_for_a_one_off(name)

        os.kill(pid, ending)
        owner.wait(GENEROUS_WAIT_S)

        wait_until_nothing_left(name)
        wait_until_gone(tmp_path.resolve() / "runs" / name)
    finally:
        remove_everything_of(name)


@pytest.mark.parametrize("ending", [signal.SIGINT, signal.SIGKILL], ids=["ctrl-c", "killed"])
def test_an_owner_that_ends_during_an_install_leaves_only_the_cache(tmp_path, ending):
    name = f"cstudy-i-hung-{ending.name.lower()}-{os.getpid()}"
    try:
        owner, pid = owner_process(tmp_path, name, INSTALL_OWNER)
        wait_for_a_one_off(name)

        os.kill(pid, ending)
        owner.wait(GENEROUS_WAIT_S)

        wait_until_no_container_or_network(name)
        wait_until_gone(tmp_path.resolve() / "runs" / name)
    finally:
        remove_everything_of(name)


def test_the_sweep_removes_a_one_off_with_a_dead_owner(engine, tmp_path):
    """The guard died too, and the one-off's client with it."""
    name = stack_name("sweptoneoff")
    plan = plan_of(tmp_path, name)
    dead = plan_with_identity(
        plan, StackIdentity(name, StackKind.TEST, "testworkspace", "sample", _dead_pid())
    )
    try:
        engine.start(dead, BUDGET)
        started = docker(
            *("compose", "--ansi", "never", "-p", name, "-f", plan.paths.in_run("stack.yaml")),
            *("run", "-d", "--no-deps", "--pull", "never", "app", *HANGS),
        )
        assert started.returncode == 0, started.stderr
        assert running_one_offs(name)

        sweep_leftovers(engine, "testworkspace", lambda _line: None)

        assert nothing_left(name)
    finally:
        remove_everything_of(name)


def wait_until_gone(path: Path) -> None:
    deadline = time.monotonic() + GENEROUS_WAIT_S
    while path.exists() and time.monotonic() < deadline:
        time.sleep(POLL_S)
    assert not path.exists()


def test_the_sweep_removes_a_dead_owners_stack_and_nothing_unlabelled(engine, tmp_path):
    """The guard can die too. The decoys carry a label of this test's and none of cstudy's."""
    name = stack_name("swept")
    decoy_label = f"cstudy-test-decoy={os.getpid()}"
    network = f"decoy-network-{os.getpid()}"
    volume = f"decoy-volume-{os.getpid()}"
    container = f"decoy-container-{os.getpid()}"
    docker("network", "create", "--label", decoy_label, network)
    docker("volume", "create", "--label", decoy_label, volume)
    docker("create", "--label", decoy_label, "--name", container, PYTHON_IMAGE, "true")
    plan = plan_of(tmp_path, name)
    dead = StackIdentity(name, StackKind.TEST, "testworkspace", "sample", _dead_pid())
    try:
        engine.start(plan_with_identity(plan, dead), BUDGET)
        assert resources_of(name)["containers"]

        found = sweep_leftovers(engine, "testworkspace", lambda _line: None)

        assert [stack.name for stack in found.stacks] == [name]
        assert nothing_left(name)
        assert docker("network", "inspect", network).returncode == 0
        assert docker("volume", "inspect", volume).returncode == 0
        assert docker("inspect", container).returncode == 0
    finally:
        engine.stop(plan)
        docker("rm", "-f", container)
        docker("network", "rm", network)
        docker("volume", "rm", volume)


def test_the_sweep_ignores_a_container_labelled_with_a_path(engine, tmp_path):
    """Anyone can run a container with cstudy's labels: this one names a folder to delete."""
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "kept").write_text("x")
    container = f"decoy-path-{os.getpid()}"
    label = os.path.relpath(victim, tmp_path / "runs")
    created = docker(
        "create",
        "--name",
        container,
        "--label",
        "cstudy.kind=test",
        "--label",
        "cstudy.workspace=testworkspace",
        "--label",
        f"com.docker.compose.project={label}",
        PYTHON_IMAGE,
        "true",
    )
    assert created.returncode == 0, created.stderr
    try:
        found = sweep_leftovers(engine, "testworkspace", lambda _line: None)

        assert [stack.name for stack in found.stacks] == []
        assert (victim / "kept").exists()
        assert docker("inspect", container).returncode == 0
    finally:
        docker("rm", "-f", container)


def plan_with_identity(plan: StackPlan, identity: StackIdentity) -> StackPlan:
    return StackPlan(identity, plan.user, plan.paths, plan.app)


def _dead_pid() -> int:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


def test_the_sweep_keeps_a_stack_whose_owner_lives(stack):
    engine, plan, _ = stack

    found = sweep_leftovers(engine, "testworkspace", lambda _line: None)

    assert plan.identity.name not in [item.name for item in found.stacks]
    assert resources_of(plan.identity.name)["containers"]


def install_plan_of(tmp_path: Path, name: str, command: tuple[str, ...]) -> InstallPlan:
    project = project_in(tmp_path)
    return InstallPlan(
        identity=StackIdentity(name, StackKind.INSTALL, "testworkspace", "sample", os.getpid()),
        user=SandboxUser(os.getuid(), os.getgid()),
        paths=SandboxPaths(str(project), str(tmp_path.resolve() / "runs" / name)),
        image=PYTHON_IMAGE,
        command=command,
        environment={"MY_CACHE": "/cache/mine"},
    )


def test_install_writes_into_the_project_and_its_cache_survives_its_down(engine, tmp_path):
    name = f"cstudy-i-sample-{os.getpid()}"
    command = (
        "python",
        "-I",
        "-c",
        "import os;os.makedirs(os.environ['MY_CACHE'],exist_ok=True);"
        "open(os.environ['MY_CACHE']+'/kept','w').write('x');open('installed.txt','w').write('y')",
    )
    plan = install_plan_of(tmp_path, name, command)
    volume = f"{name}_cache"
    try:
        with engine.guard(plan.identity):
            outcome = engine.install(plan, GENEROUS_WAIT_S, None)
            engine.stop_install(plan)

        assert outcome.exit_code == 0, outcome.output
        assert (Path(plan.paths.project) / "installed.txt").read_text() == "y"
        assert docker("volume", "inspect", volume).returncode == 0
        assert not resources_of(name)["containers"]
    finally:
        docker("volume", "rm", volume)


VENDOR: dict[str, object] = {
    "routes": [
        {
            "id": "rooms",
            "method": "GET",
            "path": "/v1/rooms",
            "response": {"status": 200, "body_file": "bodies/rooms.json"},
        }
    ],
    "scenarios": {
        "open": {"visible": True, "status": 503},
        "secret_scenario": {"status": 429, "headers": {"Retry-After": "1"}},
    },
}
BODY = '{"rooms": ["oak"]}'
TOKEN = "a-token-only-the-mock-container-holds"


def plan_with_mocks(tmp_path: Path, name: str, reach: ScenarioReach) -> StackPlan:
    files = {"room-vendor": MockFiles(VENDOR, {"bodies/rooms.json": BODY})}
    mocks = MockServerInput(("room-vendor",), TOKEN, rendered_mock_config(files, TOKEN, reach))
    return plan_of(tmp_path, name, mocks=mocks)


@pytest.fixture
def mock_stack(
    engine: DockerSandbox, tmp_path: Path
) -> Generator[tuple[DockerSandbox, StackPlan, ReadyStack]]:
    plan = plan_with_mocks(tmp_path, stack_name("mocks"), ScenarioReach.EVERY)
    with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
        yield engine, plan, ready


def endpoints_of(ready: ReadyStack) -> StackEndpoints:
    return StackEndpoints(ready.app_url, ready.control_url, TOKEN, ("room-vendor",))


FETCH_VENDOR = textwrap.dedent(
    """\
    import urllib.error, urllib.request
    try:
        with urllib.request.urlopen("http://room-vendor:8080/v1/rooms", timeout=30) as answer:
            print(json.dumps({"status": answer.status, "body": answer.read().decode()}))
    except urllib.error.HTTPError as error:
        print(json.dumps({"status": error.code, "body": ""}))
    """
)


def test_the_app_reaches_a_mock_server_at_its_stable_name(mock_stack):
    assert probe(mock_stack, FETCH_VENDOR) == {"status": 200, "body": BODY}


def test_a_scenario_set_from_here_reaches_what_the_app_gets(mock_stack):
    _, _, ready = mock_stack

    control = open_stack_clients(endpoints_of(ready)).mocks

    assert control.set_scenario("room-vendor", "open")
    assert probe(mock_stack, FETCH_VENDOR)["status"] == 503


def test_the_control_interface_keeps_a_log_and_refuses_no_token(mock_stack):
    _, _, ready = mock_stack
    probe(mock_stack, FETCH_VENDOR)

    log = open_stack_clients(endpoints_of(ready)).mocks.log("room-vendor")

    assert [entry.route for entry in log.entries] == ["rooms"]
    assert get(ready.control_port, "/mocks/room-vendor/log")[0] == 401


def test_nothing_of_the_mock_servers_is_in_the_app_container(mock_stack):
    found = probe(
        mock_stack,
        textwrap.dedent(
            f"""\
            print(json.dumps({{
                "cstudy": os.path.exists("/cstudy"),
                "mounts": "mocks.json" in open("/proc/self/mounts").read(),
                "token": any("{TOKEN}" in value for value in os.environ.values()),
            }}))
            """
        ),
    )

    assert found == {"cstudy": False, "mounts": False, "token": False}


def test_the_rendering_of_a_practice_stack_holds_no_hidden_scenario(engine, tmp_path):
    plan = plan_with_mocks(tmp_path, stack_name("visible"), ScenarioReach.VISIBLE)
    with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
        control = open_stack_clients(endpoints_of(ready)).mocks

        assert control.set_scenario("room-vendor", "open")
        assert not control.set_scenario("room-vendor", "secret_scenario")


def test_no_egress_reaches_anything_from_the_sandbox_network(stack):
    engine, plan, _ = stack

    outcome = engine.probe_egress(plan)

    assert outcome.exit_code == 0, outcome.output
    assert "reached []" in outcome.output
    assert "ipv6 []" in outcome.output


def test_the_sandbox_network_has_ipv6_off_and_no_ipv6_subnet(stack):
    _, plan, _ = stack

    shown = docker(
        "network",
        "inspect",
        "--format",
        "{{.EnableIPv6}} {{range .IPAM.Config}}{{.Subnet}} {{end}}",
        f"{plan.identity.name}_sandbox",
    )

    assert shown.returncode == 0, shown.stderr
    enabled, *subnets = shown.stdout.split()
    assert enabled == "false"
    assert not any(":" in subnet for subnet in subnets)


@pytest.fixture
def ipv6_network() -> Generator[str]:
    """Our own network with IPv6 on, whatever the engine's default: made, used and removed here."""
    name = f"cstudy-t-{os.getpid()}-ipv6"
    created = docker(
        *("network", "create", "--internal", "--ipv6", "--subnet", IPV6_SUBNET),
        *("--label", IPV6_KIND_LABEL, name),
    )
    if created.returncode != 0:
        pytest.skip(f"the engine refuses an IPv6 user network: {created.stderr.strip()}")
    try:
        yield name
    finally:
        docker("network", "rm", name)


def test_the_probe_finds_the_address_a_network_with_ipv6_on_gives(ipv6_network):
    ran = docker(
        *("run", "--rm", "--pull", "never", "--network", ipv6_network),
        *("--label", IPV6_KIND_LABEL, PYTHON_IMAGE, "python", "-I", "-c", EGRESS_PROBE),
    )

    assert ran.returncode == 1, ran.stdout + ran.stderr
    assert "ipv6 ['fd00:c5d::" in ran.stdout


DYING_SERVER = textwrap.dedent(
    """\
    import http.server, os


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/die":
                print("about to die", flush=True)
                os._exit(7)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *arguments):
            pass


    print("listening", flush=True)
    http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), Handler).serve_forever()
    """
)
COUNTING_BOOTSTRAP = (
    "python",
    "-I",
    "-c",
    "open(__import__('os').environ['CSTUDY_DATA_DIR'] + '/ran', 'a').write('x')",
)


def dying_plan(tmp_path: Path, name: str) -> StackPlan:
    plan = plan_of(tmp_path, name, bootstrap=OneShot(COUNTING_BOOTSTRAP))
    (Path(plan.paths.project) / "server.py").write_text(DYING_SERVER)
    return plan


def kill_the_app(ready: ReadyStack) -> None:
    with suppress(OSError, http.client.HTTPException):
        get(ready.app_port, "/die")


def test_a_restart_keeps_the_port_and_does_not_run_bootstrap_again(engine, tmp_path):
    plan = dying_plan(tmp_path, stack_name("restart"))
    with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
        engine.restart_app(plan, ready, BUDGET)

        assert get(ready.app_port)[0] == 200
        read = ContainerCommand(("python", "-I", "-c", READ_RAN), {}, GENEROUS_WAIT_S)
        assert engine.exec_app(plan, read).output.strip() == "x"


READ_RAN = "print(open(__import__('os').environ['CSTUDY_DATA_DIR'] + '/ran').read())"


def test_a_stopped_app_lets_a_one_off_run_then_comes_back_on_its_port(engine, tmp_path):
    plan = dying_plan(tmp_path, stack_name("oneoff"))
    with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
        engine.stop_app(plan)

        one_off = ContainerCommand(("python", "-I", "-c", "print('ran')"), {}, GENEROUS_WAIT_S)
        assert engine.run_one_off(plan, one_off).exit_code == 0

        engine.start_app(plan, ready, BUDGET)
        assert get(ready.app_port)[0] == 200


def test_an_app_that_dies_shows_its_exit_code_and_output(engine, tmp_path):
    plan = dying_plan(tmp_path, stack_name("dies"))
    with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
        assert engine.app_exit(plan, 0) is None

        kill_the_app(ready)
        ended = engine.app_exit(plan, int(GENEROUS_WAIT_S * 1000))

        assert ended is not None
        assert ended.exit_code == 7
        assert "about to die" in ended.output


def test_following_the_app_hears_it_and_ends_when_it_ends(engine, tmp_path):
    plan = dying_plan(tmp_path, stack_name("follow"))
    lines: list[str] = []
    with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
        follower = threading.Thread(
            target=engine.follow_app, args=(plan, lines.append), daemon=True
        )
        follower.start()
        kill_the_app(ready)
        follower.join(GENEROUS_WAIT_S)

        assert not follower.is_alive()
        assert "listening" in lines


def test_a_dev_stack_keeps_its_data_after_a_stop_and_a_new_owner_reads_it(engine, tmp_path):
    name = f"cstudy-d-sample-{os.getpid()}"
    identity = StackIdentity(name, StackKind.DEV, "testworkspace", "sample", os.getpid())
    write = (
        "python",
        "-I",
        "-c",
        "open(__import__('os').environ['CSTUDY_DATA_DIR'] + '/kept', 'w').write('still here')",
    )
    read = (
        "python",
        "-I",
        "-c",
        "print(open(__import__('os').environ['CSTUDY_DATA_DIR'] + '/kept').read())",
    )
    plan = plan_of(tmp_path, name, identity=identity)
    volume = f"{name}_data"
    try:
        with running_stack(engine, plan, BUDGET, lambda _line: None):
            engine.exec_app(plan, ContainerCommand(write, {}, GENEROUS_WAIT_S))

        assert docker("volume", "inspect", volume).returncode == 0
        assert not resources_of(name)["containers"]
        with running_stack(engine, plan, BUDGET, lambda _line: None):
            kept = engine.exec_app(plan, ContainerCommand(read, {}, GENEROUS_WAIT_S))

        assert kept.output.strip() == "still here"
    finally:
        docker("volume", "rm", volume)
