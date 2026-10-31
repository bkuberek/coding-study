"""Jobs over HTTP (docs/specs/web-ui.md#jobs): `doctor --fix` behind its question, `verify` of your
own problems and `bench`, their lines as a stream, one job at a time, and `doctor --fix` and runs
excluding each other, with a scripted child in place of `cstudy`."""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import OverlayProblemFiles, OverlayProblemRepository
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.runs import Children
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.scripted_runs import (
    PASSING_RUN,
    QUICK,
    Script,
    eventually,
    frames,
    lines_of,
    outs,
)
from tests.web_server import WRITE_HEADERS, session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
OWN_PROBLEM = "problems/5001-two-sum"
JOBS = "/api/v1/jobs"
DOCTOR_FIX = {"command": "doctor_fix", "confirm": True}
QUESTION = (
    "Run cstudy doctor --fix? It writes missing workspace files, refreshes the runner runtime, "
    "migrates progress.db, and runs uv sync, pnpm install and the Gradle warm-up, which may need "
    "the network."
)


@pytest.fixture
def workspace(tmp_path) -> Environment:
    """A catalog holding lru-cache, and a workspace whose own problem is two-sum."""
    catalog = repository_root(tmp_path / "catalog", PRACTICE)
    shutil.rmtree(catalog / "problems" / "0001-two-sum")
    root = repository_root(tmp_path / "workspace", PRACTICE)
    shutil.rmtree(root / "problems" / "0002-lru-cache")
    (root / "problems" / "0001-two-sum").rename(root / OWN_PROBLEM)
    meta = root / OWN_PROBLEM / "meta.yaml"
    meta.write_text(meta.read_text().replace('id: "0001"', 'id: "5001"'))
    return make_environment(
        root,
        content_root=catalog,
        problems=OverlayProblemRepository(FsProblemRepository(catalog), root),
        files=OverlayProblemFiles(FsProblemFiles(catalog), root),
        toolchains=FakeToolchains(stub_generators=STUBS),
    )


@pytest.fixture
def script(tmp_path) -> Script:
    script = Script(tmp_path / "script.json")
    script.play({"out": "ok    workspace"}, {"err": "warning: slow"}, {"exit": 0})
    return script


@pytest.fixture
def printed() -> list[tuple[str, str]]:
    return []


@pytest.fixture
def client(tmp_path, workspace, script, printed) -> Iterator[TestClient]:
    children = Children(QUICK, lambda label, text: printed.append((label, text)))
    with session_client(web_app(tmp_path, workspace, script.child, children)) as client:
        yield client


def start(client: TestClient, body: dict[str, object]):
    return client.post(JOBS, json=body, headers=WRITE_HEADERS)


def started(client: TestClient, body: dict[str, object]) -> str:
    response = start(client, body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def events(client: TestClient, job_id: str) -> str:
    return client.get(f"{JOBS}/{job_id}/events").text


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


@pytest.fixture
def holding(script) -> Path:
    gate = script.gate("release")
    script.play({"out": "working"}, {"wait_for": str(gate)}, {"exit": 0})
    return gate


# doctor --fix


def test_doctor_fix_without_confirm_asks_its_question(client):
    response = start(client, {"command": "doctor_fix"})
    assert (error(response), response.json()["error"]["message"]) == (
        (409, "confirmation_required"),
        QUESTION,
    )


def test_doctor_fix_without_confirm_starts_nothing(client, script):
    start(client, {"command": "doctor_fix"})
    assert script.calls() == []


def test_a_confirmed_doctor_fix_is_cstudy_doctor_fix(client, script):
    started(client, DOCTOR_FIX)
    assert script.arguments() == ["doctor", "--fix"]


def test_a_jobs_lines_stream_from_both_outputs(client):
    job_id = started(client, DOCTOR_FIX)
    lines = list(lines_of(frames(events(client, job_id)), "line"))
    assert sorted(lines, key=lambda line: line["stream"]) == [
        {"stream": "stderr", "text": "warning: slow"},
        {"stream": "stdout", "text": "ok    workspace"},
    ]


def test_a_job_closes_with_its_exit_code(client):
    closed = frames(events(client, started(client, DOCTOR_FIX)))[-1]
    assert (closed.event, closed.data["exit_code"]) == ("closed", 0)


def test_the_server_prints_a_line_when_a_job_ends(client, printed):
    events(client, started(client, DOCTOR_FIX))
    assert printed == [("job", "doctor --fix · exit 0")]


def test_a_jobs_document(client):
    job_id = started(client, DOCTOR_FIX)
    events(client, job_id)
    document = client.get(f"{JOBS}/{job_id}").json()
    del document["started_at"]
    assert document == {
        "id": job_id,
        "command": "doctor_fix",
        "options": {},
        "state": "ended",
        "exit_code": 0,
    }


# verify and bench


def test_verify_of_your_own_problem_is_cstudy_verify(client, script):
    started(client, {"command": "verify", "slugs": ["two-sum"], "static": True})
    assert script.arguments() == ["verify", "--static", "--", "two-sum"]


def test_verify_of_a_catalog_problem_is_refused(client):
    response = start(client, {"command": "verify", "slugs": ["lru-cache"]})
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "the page verifies your own problems; "
        "run cstudy verify in a content checkout for catalog problems",
    )


def test_verify_of_an_unknown_problem_is_not_found(client):
    assert error(start(client, {"command": "verify", "slugs": ["no-such"]})) == (404, "not_found")


def test_verify_needs_a_problem(client):
    assert error(start(client, {"command": "verify", "slugs": []})) == (422, "usage")


def test_bench_is_cstudy_bench_of_the_problem(client, script):
    body = {
        "command": "bench",
        "slug": "two-sum",
        "language": "kotlin",
        "sizes": [100, 1000],
        "reps": 3,
        "refs_only": True,
        "no_memory": True,
    }
    started(client, body)
    assert script.arguments() == [
        "bench",
        "--lang=kotlin",
        "--sizes=100,1000",
        "--reps=3",
        "--refs-only",
        "--no-memory",
        "--",
        "two-sum",
    ]


@pytest.mark.parametrize(
    "body",
    [
        {"command": "bench", "slug": "two-sum", "language": "cobol"},
        {"command": "bench", "slug": "two-sum", "language": "python", "reps": 51},
        {"command": "bench", "slug": "two-sum", "language": "python", "sizes": [0]},
        {"command": "bench", "language": "python"},
        {"command": "doctor_fix", "confirm": True, "slugs": ["two-sum"]},
        {"command": "shell"},
    ],
)
def test_a_job_option_of_the_wrong_name_type_or_range_is_a_usage_error(client, body):
    assert error(start(client, body)) == (422, "usage")


# the slot


def test_a_second_job_gets_409_with_the_running_jobs_id(client, holding):
    job_id = started(client, DOCTOR_FIX)
    response = start(client, {"command": "verify", "slugs": ["two-sum"]})
    assert (error(response), response.json()["error"]["job"]) == ((409, "conflict"), job_id)


def test_a_job_may_start_once_the_last_one_ended(client, holding):
    job_id = started(client, DOCTOR_FIX)
    holding.touch()
    events(client, job_id)
    assert start(client, DOCTOR_FIX).status_code == 201


def test_no_run_starts_while_doctor_fix_runs(client, workspace, holding):
    attempt_id = start_attempt(workspace, StartRequest("two-sum", Language.PYTHON)).attempt.id
    job_id = started(client, DOCTOR_FIX)
    body = {"attempt_id": attempt_id, "command": "test"}
    response = client.post("/api/v1/runs", json=body, headers=WRITE_HEADERS)
    assert (error(response), response.json()["error"]["job"]) == ((409, "conflict"), job_id)


def test_doctor_fix_does_not_start_while_a_run_runs(client, workspace, script, holding):
    attempt_id = start_attempt(workspace, StartRequest("two-sum", Language.PYTHON)).attempt.id
    script.play(*outs(*PASSING_RUN), {"wait_for": str(holding)}, {"exit": 0})
    body = {"attempt_id": attempt_id, "command": "test"}
    run_id = client.post("/api/v1/runs", json=body, headers=WRITE_HEADERS).json()["id"]
    response = start(client, DOCTOR_FIX)
    assert (error(response), response.json()["error"]["run"]) == ((409, "conflict"), run_id)


def test_another_job_may_run_beside_a_run(client, workspace, script, holding):
    attempt_id = start_attempt(workspace, StartRequest("two-sum", Language.PYTHON)).attempt.id
    script.play(*outs(*PASSING_RUN), {"wait_for": str(holding)}, {"exit": 0})
    body = {"attempt_id": attempt_id, "command": "test"}
    client.post("/api/v1/runs", json=body, headers=WRITE_HEADERS)
    assert start(client, {"command": "verify", "slugs": ["two-sum"]}).status_code == 201


# cancel and retention


def test_cancelling_a_job_stops_its_child(client, script):
    script.play({"out": "working"})
    job_id = started(client, DOCTOR_FIX)
    eventually(script.calls, bool)
    cancel = client.post(f"{JOBS}/{job_id}/cancel", headers=WRITE_HEADERS)
    closed = frames(events(client, job_id))[-1]
    assert (cancel.status_code, closed.data["exit_code"] != 0) == (202, True)


def test_the_server_keeps_the_last_ten_jobs(client):
    first = started(client, DOCTOR_FIX)
    events(client, first)
    for _ in range(10):
        events(client, started(client, DOCTOR_FIX))
    assert error(client.get(f"{JOBS}/{first}")) == (404, "not_found")
