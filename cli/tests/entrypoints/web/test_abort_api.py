"""`POST /api/v1/attempts/{id}/abort`: the page's Abort, as `cstudy abort`
(docs/specs/web-ui.md#attempts). Like the CLI it asks first: without `confirm` the server answers
409 `confirmation_required` with the CLI's question and changes nothing."""

from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.runs import Children
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.scripted_runs import QUICK, Script
from tests.web_server import WRITE_HEADERS, session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
STUB = "python/practice/two_sum.py"
MINE = "def two_sum(): ...\n"


@pytest.fixture
def environment(tmp_path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    return make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))


@pytest.fixture
def attempt(environment) -> Attempt:
    started = start_attempt(environment, StartRequest("two-sum", Language.PYTHON)).attempt
    environment.workspace.write_text(STUB, MINE)
    return started


def abort_path(attempt: Attempt) -> str:
    return f"/api/v1/attempts/{attempt.id}/abort"


def post(tmp_path: Path, environment, attempt: Attempt, **body: object):
    with session_client(web_app(tmp_path, environment)) as client:
        return client.post(abort_path(attempt), json=body, headers=WRITE_HEADERS)


def status_of(environment, attempt: Attempt) -> AttemptStatus:
    found = environment.progress.attempt(attempt.id)
    assert found is not None
    return found.status


def test_without_the_confirmation_the_server_asks_the_clis_question(tmp_path, environment, attempt):
    response = post(tmp_path, environment, attempt)
    assert (response.status_code, response.json()["error"]["code"]) == (
        409,
        "confirmation_required",
    )
    assert response.json()["error"]["message"] == (
        "Abort two-sum in python? The attempt ends as abandoned. "
        "Your files stay; progress and the review schedule do not change."
    )


def test_without_the_confirmation_nothing_changes(tmp_path, environment, attempt):
    post(tmp_path, environment, attempt)
    assert status_of(environment, attempt) is AttemptStatus.IN_PROGRESS


def test_with_the_confirmation_the_attempt_is_abandoned(tmp_path, environment, attempt):
    response = post(tmp_path, environment, attempt, confirm=True)
    assert (response.status_code, status_of(environment, attempt)) == (
        200,
        AttemptStatus.ABANDONED,
    )


def test_the_answer_names_the_attempt_and_the_file_that_stays(tmp_path, environment, attempt):
    document = post(tmp_path, environment, attempt, confirm=True).json()
    assert document == {
        "attempt_id": attempt.id,
        "slug": "two-sum",
        "language": "python",
        "status": "abandoned",
        "kept": STUB,
    }


def test_the_practice_file_stays(tmp_path, environment, attempt):
    post(tmp_path, environment, attempt, confirm=True)
    assert environment.workspace.read_text(STUB) == MINE


def test_the_attempt_is_gone_from_the_problems_in_progress(tmp_path, environment, attempt):
    post(tmp_path, environment, attempt, confirm=True)
    with session_client(web_app(tmp_path, environment)) as client:
        listed = client.get("/api/v1/problems").json()["entries"]
    two_sum = next(entry for entry in listed if entry["slug"] == "two-sum")
    assert (two_sum["status"], two_sum["in_progress"]) == ("new", [])


def test_an_attempt_that_ended_gets_409_attempt_ended(tmp_path, environment, attempt):
    post(tmp_path, environment, attempt, confirm=True)
    response = post(tmp_path, environment, attempt, confirm=True)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "attempt_ended")


def test_an_unknown_attempt_gets_404(tmp_path, environment):
    with session_client(web_app(tmp_path, environment)) as client:
        response = client.post(
            "/api/v1/attempts/999/abort", json={"confirm": True}, headers=WRITE_HEADERS
        )
    assert response.status_code == 404


def test_a_running_child_refuses_and_names_the_run(tmp_path):
    root = repository_root(tmp_path / "workspace", PRACTICE, FIXTURE_TRACKS)
    environment = make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))
    attempt = start_attempt(environment, StartRequest("two-sum", Language.PYTHON)).attempt
    script = Script(tmp_path / "script.json")
    gate = script.gate("let-it-end")
    script.play({"wait_for": str(gate)}, {"exit": 0})
    app = web_app(root, environment, script.child, Children(QUICK))
    with session_client(app) as client:
        started = client.post(
            "/api/v1/runs",
            json={"attempt_id": attempt.id, "command": "test"},
            headers=WRITE_HEADERS,
        )
        refused = client.post(abort_path(attempt), json={"confirm": True}, headers=WRITE_HEADERS)
        gate.write_text("")
    assert (refused.status_code, refused.json()["error"]["run"]) == (409, started.json()["id"])
    assert status_of(environment, attempt) is AttemptStatus.IN_PROGRESS
