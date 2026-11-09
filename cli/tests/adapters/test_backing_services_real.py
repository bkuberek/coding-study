"""A problem's backing service merged into a stack, on a real Docker engine, with resources this
test labels and removes. Run with `uv run pytest -q -m docker`. The service is a small HTTP server
on the pinned Python image, so nothing is pulled; the Postgres and Redis fixture exercises real
engines in `tests/test_service_projects_real.py`."""

import http.client
import json
import os
import subprocess
import textwrap
from collections.abc import Generator
from pathlib import Path

import pytest

from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
from coding_study.application.ports import ContainerCommand
from coding_study.application.sandbox import running_stack
from coding_study.domain.sandbox import (
    LABEL_KIND,
    PYTHON_IMAGE,
    AppContainer,
    BackingServices,
    ReadyStack,
    SandboxPaths,
    SandboxUser,
    StackIdentity,
    StackKind,
    StackPlan,
    StartupBudget,
)
from tests.waits import GENEROUS_WAIT_S

pytestmark = [pytest.mark.slow, pytest.mark.docker]

BUDGET = StartupBudget(up_s=int(GENEROUS_WAIT_S), app_ready_s=int(GENEROUS_WAIT_S))
ORIGIN = "echo:8080"
APP = textwrap.dedent(
    """\
    import http.server, os


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()


    http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), Handler).serve_forever()
    """
)
ECHO = textwrap.dedent(
    """\
    import http.server, json, pathlib

    STORE = pathlib.Path("/var/lib/echo/hits")


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits = int(STORE.read_text()) + 1 if STORE.exists() else 1
            STORE.write_text(str(hits))
            seed = pathlib.Path("/seed/seed.txt").read_text()
            body = json.dumps({"host": self.headers["Host"], "hits": hits, "seed": seed})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *arguments):
            pass


    http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
    """
)
LISTENS = "import socket; socket.create_connection(('127.0.0.1', 8080), 1)"
COMPOSE: dict[str, object] = {
    "services": {
        "echo": {
            "image": PYTHON_IMAGE,
            "command": ["python", "-I", "/echo/echo.py"],
            "volumes": [
                "hits:/var/lib/echo",
                "./echo.py:/echo/echo.py",
                "./seed:/seed",
            ],
            "mem_limit": "64m",
            "pids_limit": 32,
            "healthcheck": {
                "test": ["CMD", "python", "-I", "-c", LISTENS],
                "interval": "30s",
                "start_period": "60s",
                "start_interval": "250ms",
            },
        }
    },
    "volumes": {"hits": None},
}
STATUS = (
    "lines = dict(l.split(':', 1) for l in open('/proc/self/status') if ':' in l)\n"
    "print(lines['CapEff'].strip(), lines['NoNewPrivs'].strip())"
)
WRITES = (
    "import sys\n"
    "for path in sys.argv[1:]:\n"
    "    try:\n"
    "        open(path, 'w').write('x')\n"
    "        print(path, 'written')\n"
    "    except OSError:\n"
    "        print(path, 'refused')"
)
EGRESS = (
    "import socket\n"
    "for target in (('1.1.1.1', 443), ('169.254.169.254', 80)):\n"
    "    try:\n"
    "        socket.create_connection(target, 2).close()\n"
    "        print('reached', target)\n"
    "    except OSError:\n"
    "        pass"
)


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


def plan_in(tmp_path: Path, kind: StackKind, name: str) -> StackPlan:
    project = tmp_path.resolve() / "workspace" / "projects" / "sample"
    project.mkdir(parents=True, exist_ok=True)
    (project / "server.py").write_text(APP)
    services = tmp_path.resolve() / "problem" / "services"
    (services / "seed").mkdir(parents=True, exist_ok=True)
    (services / "echo.py").write_text(ECHO)
    (services / "seed" / "seed.txt").write_text("from the problem")
    return StackPlan(
        identity=StackIdentity(name, kind, "testworkspace", "sample", os.getpid()),
        user=SandboxUser(os.getuid(), os.getgid()),
        paths=SandboxPaths(str(project), str(tmp_path.resolve() / "runs" / name)),
        app=AppContainer(PYTHON_IMAGE, ("python", "-I", "server.py"), 8000, {"PORT": "8000"}),
        backing=BackingServices(COMPOSE, str(services)),
        reach=(ORIGIN,) if kind.serves_the_grader else (),
    )


def resources_of(name: str) -> list[str]:
    label = f"label=com.docker.compose.project={name}"
    return [
        *docker("ps", "-aq", "--filter", label).stdout.split(),
        *docker("network", "ls", "-q", "--filter", label).stdout.split(),
        *docker("volume", "ls", "-q", "--filter", label).stdout.split(),
    ]


def remove_everything_of(name: str) -> None:
    """What a failing test would otherwise leave on the engine; nothing when it passed."""
    label = f"label=com.docker.compose.project={name}"
    containers = docker("ps", "-aq", "--filter", label).stdout.split()
    if containers:
        docker("rm", "-f", "-v", *containers)
    for network in docker("network", "ls", "-q", "--filter", label).stdout.split():
        docker("network", "rm", network)
    for volume in docker("volume", "ls", "-q", "--filter", label).stdout.split():
        docker("volume", "rm", volume)


@pytest.fixture
def engine(tmp_path: Path) -> DockerSandbox:
    return DockerSandbox(SubprocessDockerRunner(), runs_directory=tmp_path / "runs")


@pytest.fixture
def stack(engine: DockerSandbox, tmp_path: Path) -> Generator[tuple[StackPlan, ReadyStack]]:
    name = f"cstudy-t-{os.getpid()}-backing"
    plan = plan_in(tmp_path, StackKind.TEST, name)
    try:
        with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
            yield plan, ready
    finally:
        remove_everything_of(name)


def in_service(plan: StackPlan, code: str, *arguments: str) -> str:
    container = docker(
        "ps",
        "-q",
        "--filter",
        f"label=com.docker.compose.project={plan.identity.name}",
        "--filter",
        "label=com.docker.compose.service=echo",
    ).stdout.strip()
    found = docker("exec", container, "python", "-I", "-c", code, *arguments)
    assert found.returncode == 0, found.stderr
    return found.stdout.strip()


def ask_echo(url: str, host: str = ORIGIN) -> dict[str, object]:
    address = url.removeprefix("http://")
    connection = http.client.HTTPConnection(address, timeout=GENEROUS_WAIT_S)
    try:
        connection.request("GET", "/", headers={"Host": host})
        return json.loads(connection.getresponse().read())
    finally:
        connection.close()


def test_the_app_reaches_a_backing_service_at_its_stable_name(engine, stack):
    plan, _ = stack
    code = (
        "import urllib.request; print(urllib.request.urlopen('http://echo:8080/').read().decode())"
    )

    found = engine.exec_app(plan, _command(code))

    assert json.loads(found.output)["host"] == ORIGIN


def test_the_grader_reaches_a_declared_service_with_the_original_host(stack):
    _, ready = stack

    assert ask_echo(ready.reach_urls[ORIGIN])["host"] == ORIGIN


def test_a_file_the_problem_mounts_reaches_its_service(stack):
    _, ready = stack

    assert ask_echo(ready.reach_urls[ORIGIN])["seed"] == "from the problem"


def test_a_backing_service_holds_no_capability_and_cannot_gain_one(stack):
    plan, _ = stack

    assert in_service(plan, STATUS) == "0000000000000000 1"


def test_a_backing_service_writes_its_volume_and_nothing_else(stack):
    plan, _ = stack

    found = in_service(plan, WRITES, "/var/lib/echo/x", "/etc/x", "/seed/x", "/echo/x")

    assert found.splitlines() == [
        "/var/lib/echo/x written",
        "/etc/x refused",
        "/seed/x refused",
        "/echo/x refused",
    ]


def test_a_backing_service_reaches_nothing_beyond_the_sandbox(stack):
    plan, _ = stack

    assert in_service(plan, EGRESS) == ""


def test_a_backing_services_volume_carries_the_stacks_labels(stack):
    plan, _ = stack
    volume = f"{plan.identity.name}_hits"

    kind = docker("volume", "inspect", "--format", f'{{{{index .Labels "{LABEL_KIND}"}}}}', volume)

    assert kind.stdout.strip() == "test"


def test_a_test_stack_leaves_nothing_of_its_backing_services(engine, tmp_path):
    name = f"cstudy-t-{os.getpid()}-gone"
    plan = plan_in(tmp_path, StackKind.TEST, name)
    try:
        with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
            ask_echo(ready.reach_urls[ORIGIN])

        assert resources_of(name) == []
    finally:
        remove_everything_of(name)


def test_a_dev_stack_keeps_a_backing_services_data_and_publishes_no_reach(engine, tmp_path):
    name = f"cstudy-d-sample-{os.getpid()}-backing"
    plan = plan_in(tmp_path, StackKind.DEV, name)
    code = (
        "import urllib.request; print(urllib.request.urlopen('http://echo:8080/').read().decode())"
    )
    try:
        with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
            engine.exec_app(plan, _command(code))
            assert ready.reach_urls == {}
        with running_stack(engine, plan, BUDGET, lambda _line: None):
            again = engine.exec_app(plan, _command(code))

        assert json.loads(again.output)["hits"] == 2
    finally:
        remove_everything_of(name)


def _command(code: str) -> ContainerCommand:
    return ContainerCommand(("python", "-I", "-c", code), {}, GENEROUS_WAIT_S)
