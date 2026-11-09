"""A real Docker engine: what the app prints, read for a case's window, as the output check reads
it. Run with `uv run pytest -q -m docker`; it labels and removes what it starts, and pulls
nothing."""

import http.client
import os
import subprocess
import textwrap
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
from coding_study.application.sandbox import running_stack
from coding_study.domain.sandbox import (
    PYTHON_IMAGE,
    AppContainer,
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
PRINTING_SERVER = textwrap.dedent(
    """\
    import http.server, os, sys


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            print(f"out {self.path}", flush=True)
            print(f"err {self.path}", file=sys.stderr, flush=True)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *arguments):
            pass


    http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), Handler).serve_forever()
    """
)
CLOCK_STEP_S = 1.1
"""Longer than the engine's timestamps could round across, so the two requests fall apart."""


@pytest.fixture(scope="module", autouse=True)
def require_engine() -> None:
    try:
        found = subprocess.run(
            ["docker", "image", "inspect", PYTHON_IMAGE],
            capture_output=True,
            timeout=GENEROUS_WAIT_S,
            check=False,
        )
    except FileNotFoundError:
        pytest.skip("no docker on PATH")
    if found.returncode != 0:
        pytest.skip("no running Docker engine, or the pinned Python image is not here")


@pytest.fixture
def printing_stack(tmp_path: Path) -> Generator[tuple[DockerSandbox, StackPlan, ReadyStack]]:
    project = tmp_path.resolve() / "workspace" / "projects" / "sample"
    project.mkdir(parents=True)
    (project / "server.py").write_text(PRINTING_SERVER)
    name = f"cstudy-t-{os.getpid()}-output"
    plan = StackPlan(
        StackIdentity(name, StackKind.TEST, "testworkspace", "sample", os.getpid()),
        SandboxUser(os.getuid(), os.getgid()),
        SandboxPaths(str(project), str(tmp_path.resolve() / "runs" / name)),
        AppContainer(PYTHON_IMAGE, ("python", "-I", "server.py"), 8000, {"PORT": "8000"}),
    )
    engine = DockerSandbox(SubprocessDockerRunner(), runs_directory=tmp_path / "runs")
    with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
        yield engine, plan, ready


def visit(port: int, path: str) -> None:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=GENEROUS_WAIT_S)
    try:
        connection.request("GET", path)
        connection.getresponse().read()
    finally:
        connection.close()


def test_the_output_since_a_moment_holds_what_came_after_it_on_both_streams(printing_stack):
    engine, plan, ready = printing_stack
    visit(ready.app_port, "/before")
    time.sleep(CLOCK_STEP_S)
    since = time.time()
    visit(ready.app_port, "/during")

    printed = engine.app_output_since(plan, since)

    assert ("out /during" in printed, "err /during" in printed, "/before" in printed) == (
        True,
        True,
        False,
    )
