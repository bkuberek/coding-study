"""A case that pauses, stops and starts a backing service, on a real Docker engine, with resources
this test labels and removes. Run with `uv run pytest -q -m docker`. The service is the Redis of the
fixture `5903`, and the app a small server that pings it, so nothing is pulled. Each verdict shows
what a client meets: a paused service accepts a connection and never answers, and a stopped one
has a name that no longer resolves. The cases after one that left a service changed find it back."""

import os
import textwrap
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import yaml

from coding_study.adapters.docker_sandbox import DockerSandbox, SubprocessDockerRunner
from coding_study.adapters.http_grader.clients import open_stack_clients
from coding_study.adapters.problem_documents import cases_from_document
from coding_study.application.graded_stack import RunningStack, SandboxGradedStack
from coding_study.application.http_grading import HttpGradingRun, run_http_grading
from coding_study.application.sandbox import running_stack
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.config import Config
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Problem
from coding_study.domain.sandbox import (
    PYTHON_IMAGE,
    AppContainer,
    BackingServices,
    SandboxPaths,
    SandboxUser,
    StackIdentity,
    StackKind,
    StackPlan,
)
from coding_study.domain.service_project import (
    ServiceApp,
    ServiceCommands,
    ServiceProject,
    ServiceRequires,
)
from tests.adapters.test_backing_services_real import BUDGET, docker, remove_everything_of
from tests.helpers import REPOSITORY_ROOT
from tests.project_builders import project_meta

pytestmark = [pytest.mark.slow, pytest.mark.docker]

FIXTURE_COMPOSE = (
    REPOSITORY_ROOT
    / "cli/tests/fixtures/service_projects/5903-fixture-members-python/services/compose.yaml"
)
REDIS: dict[str, Any] = yaml.safe_load(FIXTURE_COMPOSE.read_text())["services"]["cache"]
COMPOSE: dict[str, object] = {"services": {"store": REDIS}, "volumes": {"cachedata": None}}
APP = textwrap.dedent(
    """\
    import http.server, json, os, socket


    def store():
        try:
            connection = socket.create_connection(("store", 6379), 1.5)
        except socket.gaierror:
            return "unknown host"
        except ConnectionRefusedError:
            return "refused"
        except TimeoutError:
            return "connect timed out"
        with connection:
            connection.settimeout(1.5)
            connection.sendall(b"PING\\r\\n")
            try:
                return connection.recv(64).decode().strip()
            except TimeoutError:
                return "no answer"


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"store": store()}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *arguments):
            pass


    http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), Handler).serve_forever()
    """
)


def asks_store(answer: str) -> dict[str, Any]:
    return {
        "request": {"method": "GET", "path": "/store"},
        "expected": {"status": 200, "body": {"store": answer}},
    }


def store_step(action: str) -> dict[str, str]:
    return {"service": "store", "action": action}


ANSWERS = "+PONG"
CASES = {
    "version": 1,
    "cases": [
        {
            "id": "paused",
            "level": 1,
            "steps": [
                asks_store(ANSWERS),
                store_step("pause"),
                asks_store("no answer"),
                store_step("unpause"),
                asks_store(ANSWERS),
            ],
        },
        {
            "id": "stopped",
            "level": 1,
            "steps": [
                store_step("stop"),
                asks_store("unknown host"),
                store_step("start"),
                asks_store(ANSWERS),
            ],
        },
        {"id": "left-paused", "level": 1, "steps": [store_step("pause"), asks_store(ANSWERS)]},
        {"id": "after-a-pause", "level": 1, "steps": [asks_store(ANSWERS)]},
        {
            "id": "left-stopped",
            "level": 1,
            "steps": [store_step("stop"), asks_store("unknown host")],
        },
        {"id": "after-a-stop", "level": 1, "steps": [asks_store(ANSWERS)]},
    ],
}


@pytest.fixture(scope="module", autouse=True)
def require_engine_and_images() -> None:
    try:
        if docker("info", "--format", "{{.ServerVersion}}").returncode != 0:
            pytest.skip("no running Docker engine")
    except FileNotFoundError:
        pytest.skip("no docker on PATH")
    for image in (PYTHON_IMAGE, REDIS["image"]):
        if docker("image", "inspect", image).returncode != 0:
            pytest.skip(f"{image} is not here; a test pulls nothing")


def plan_in(tmp_path: Path, name: str) -> StackPlan:
    project = tmp_path.resolve() / "workspace" / "projects" / "sample"
    project.mkdir(parents=True)
    (project / "server.py").write_text(APP)
    services = tmp_path.resolve() / "problem" / "services"
    services.mkdir(parents=True)
    return StackPlan(
        identity=StackIdentity(name, StackKind.TEST, "testworkspace", "sample", os.getpid()),
        user=SandboxUser(os.getuid(), os.getgid()),
        paths=SandboxPaths(str(project), str(tmp_path.resolve() / "runs" / name)),
        app=AppContainer(PYTHON_IMAGE, ("python", "-I", "server.py"), 8000, {"PORT": "8000"}),
        backing=BackingServices(COMPOSE, str(services)),
    )


def store_service() -> ServiceProject:
    return ServiceProject(
        image=PYTHON_IMAGE,
        commands=ServiceCommands(run=("python", "-I", "server.py"), test=("true",)),
        app=ServiceApp("PORT", 8000, "/health"),
        env={"PORT": "8000"},
        requires=ServiceRequires(),
        services="services/compose.yaml",
    )


@pytest.fixture(scope="module")
def outcomes(tmp_path_factory: pytest.TempPathFactory) -> Generator[dict[str, str | None]]:
    """Each case's status, or why it failed, graded once for the module."""
    tmp_path = tmp_path_factory.mktemp("service-steps")
    engine = DockerSandbox(SubprocessDockerRunner(), runs_directory=tmp_path / "runs")
    name = f"cstudy-t-{os.getpid()}-services"
    plan = plan_in(tmp_path, name)
    comparator = ComparatorSpec(ComparatorType.EXACT)
    cases = cases_from_document(CASES, comparator, "tests.json")
    run = HttpGradingRun(Problem(project_meta(comparator=comparator), cases), 1, Config())
    try:
        with running_stack(engine, plan, BUDGET, lambda _line: None) as ready:
            stack = SandboxGradedStack(engine, RunningStack(plan, ready), store_service())
            judgement = run_http_grading(run, stack, open_stack_clients)
        yield {
            verdict.case.id: verdict.mismatch.detail if verdict.mismatch else verdict.status.value
            for verdict in judgement.verdicts
        }
    finally:
        remove_everything_of(name)


PASSED = CaseStatus.PASS.value


def test_a_paused_service_accepts_a_connection_and_never_answers(outcomes):
    assert outcomes["paused"] == PASSED


def test_a_stopped_service_has_a_name_that_no_longer_resolves(outcomes):
    assert outcomes["stopped"] == PASSED


def test_a_case_that_failed_with_its_service_paused_says_what_the_app_met(outcomes):
    assert "no answer" in (outcomes["left-paused"] or "")


def test_a_service_a_case_left_paused_is_unpaused_for_the_next(outcomes):
    assert outcomes["after-a-pause"] == PASSED


def test_a_service_a_case_left_stopped_is_started_for_the_next(outcomes):
    assert (outcomes["left-stopped"], outcomes["after-a-stop"]) == (PASSED, PASSED)
