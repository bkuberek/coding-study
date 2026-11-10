"""What a service project depends on, from the page (docs/specs/service-projects.md#where-it-shows):
the rows `cstudy show` lists, each with its state on this machine, which asks the engine and starts
nothing; and a Start that refuses, as `cstudy start` does, when Docker cannot run the project."""

from collections.abc import Iterator

import pytest
from starlette.testclient import TestClient

from coding_study.application.environment import Environment
from coding_study.domain.docker_engine import EngineState, EngineStatus
from tests.fakes import make_environment
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import FOLDER, SLUG, make_content, write_problem
from tests.web_server import WRITE_HEADERS, session_client, web_app

NEEDS = f"/api/v1/problems/{SLUG}/needs"
ATTEMPTS = "/api/v1/attempts"


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox()


@pytest.fixture
def environment(tmp_path, engine) -> Environment:
    root = make_content(tmp_path)
    write_problem(root)
    return make_environment(root, sandbox=engine)


@pytest.fixture
def client(tmp_path, environment) -> Iterator[TestClient]:
    with session_client(web_app(tmp_path, environment)) as client:
        yield client


def labels(client: TestClient) -> list[str]:
    return [row["label"] for row in client.get(NEEDS).json()["needs"]]


def docker_row(client: TestClient) -> dict[str, object]:
    return client.get(NEEDS).json()["needs"][0]


def test_the_needs_are_the_rows_cstudy_show_lists(client):
    assert labels(client) == ["docker", "language", "packages", "total"]


def test_a_running_engine_meets_the_docker_need(client):
    assert docker_row(client)["problem"] is None


def test_a_missing_engine_names_the_install_message(client, engine):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    assert "docs.docker.com" in str(docker_row(client)["problem"])


def test_a_stopped_engine_is_no_problem_and_is_not_started(client, engine):
    engine.engine = EngineState(EngineStatus.STOPPED)

    assert docker_row(client)["problem"] is None
    assert not engine.called("start_engine")


def test_another_problem_needs_nothing(client):
    assert client.get("/api/v1/problems/two-sum/needs").json() == {"needs": None}


def test_another_problem_asks_the_engine_nothing(client, engine):
    client.get("/api/v1/problems/two-sum/needs")

    assert not engine.called("state")


def test_an_unknown_problem_is_not_found(client):
    assert client.get("/api/v1/problems/no-such-problem/needs").status_code == 404


def start(client: TestClient):
    return client.post(ATTEMPTS, json={"slug": SLUG}, headers=WRITE_HEADERS)


def test_start_without_docker_is_refused_with_the_install_message(client, engine):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    response = start(client)

    assert response.status_code == 503
    assert "docs.docker.com" in response.json()["error"]["message"]


def test_start_without_docker_writes_nothing(client, engine, environment):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    start(client)

    assert not environment.workspace.exists(FOLDER)


def test_start_with_a_stopped_engine_starts_the_attempt_and_not_the_engine(client, engine):
    engine.engine = EngineState(EngineStatus.STOPPED)

    assert start(client).status_code == 201
    assert not engine.called("start_engine")


def test_start_downloads_and_installs_nothing(client, engine):
    start(client)

    assert (engine.called("pull"), engine.called("install")) == ([], [])
