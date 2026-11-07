"""A real Docker engine: the sandbox as the spike measured it, on resources this test labels and
removes. Run with `uv run pytest -q -m docker`. Waits are generous, for a busy machine; what these
tests measure is whether things happen, not how fast."""

import http.client
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
from coding_study.application.ports import ContainerCommand
from coding_study.application.sandbox import running_stack, sweep_leftovers
from coding_study.domain.sandbox import (
    PYTHON_IMAGE,
    AppContainer,
    InstallPlan,
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


def test_a_stopped_stack_leaves_nothing(engine, tmp_path):
    name = stack_name("stops")
    plan = plan_of(tmp_path, name)

    with running_stack(engine, plan, BUDGET, lambda _line: None):
        assert resources_of(name)["containers"]

    assert nothing_left(name)
    assert not Path(plan.paths.run).exists()


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

    from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
    from coding_study.application.sandbox import running_stack
    from coding_study.domain.sandbox import (
        AppContainer, SandboxPaths, SandboxUser, StackIdentity, StackKind, StackPlan, StartupBudget,
    )

    name, image, project, run = sys.argv[1:5]
    engine = DockerSandbox(SubprocessDockerRunner())
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


def owner_process(tmp_path: Path, name: str) -> tuple[subprocess.Popen[str], int]:
    project = project_in(tmp_path)
    source = Path(__file__).parents[2] / "src"
    owner = subprocess.Popen(
        [
            sys.executable,
            "-c",
            OWNER_PROGRAM,
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
