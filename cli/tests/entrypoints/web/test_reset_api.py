"""`GET` and `POST /api/v1/reset`: the Settings view's Danger section
(docs/specs/web-ui.md#session-and-preferences)."""

from pathlib import Path

import pytest

from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.runs import Children
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.scripted_runs import QUICK, Script
from tests.stats_fixture import fill_progress
from tests.web_server import WRITE_HEADERS, session_client, web_app, web_workspace

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {Language.PYTHON: FakeStubGenerator()}
RESET = "/api/v1/reset"
RUN_FILE = ".cs/runs/20261106-1/out.json"
PRACTICE_FILE = "python/practice/two_sum.py"
ARCHIVED = ".archive/two-sum/1-python/two_sum.py"


@pytest.fixture
def environment(tmp_path: Path):
    environment = web_workspace(tmp_path)
    fill_progress(environment)
    for path in (RUN_FILE, PRACTICE_FILE, ARCHIVED):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("x")
    return environment


@pytest.fixture
def app(tmp_path: Path, environment):
    return web_app(tmp_path, environment)


def attempts(environment) -> int:
    return environment.progress.snapshot().row_counts()["attempts"]


def post(client, **body: object):
    return client.post(RESET, json=body, headers=WRITE_HEADERS)


def entries(document: dict, option: str | None) -> dict[str, int]:
    group = next(group for group in document["groups"] if group["option"] == option)
    return {entry["label"]: entry["count"] for entry in group["entries"]}


def test_the_preview_counts_what_goes(app):
    with session_client(app) as client:
        document = client.get(RESET).json()
    assert (entries(document, None)["attempts"], entries(document, "files")["practice files"]) == (
        6,
        1,
    )


def test_the_preview_says_the_word_and_the_warning(app):
    with session_client(app) as client:
        document = client.get(RESET).json()
    assert (document["word"], document["warning"]) == ("reset", "This can't be undone.")


def test_the_preview_deletes_nothing(app, environment):
    with session_client(app) as client:
        client.get(RESET)
    assert attempts(environment) == 6


def test_a_plain_post_gets_409_and_deletes_nothing(app, environment, tmp_path):
    with session_client(app) as client:
        response = post(client)
    assert (
        response.status_code,
        response.json()["error"]["code"],
        attempts(environment),
        (tmp_path / RUN_FILE).exists(),
    ) == (409, "confirmation_required", 6, True)


def test_the_refusal_says_it_cannot_be_undone(app):
    with session_client(app) as client:
        assert "can't be undone" in post(client).json()["error"]["message"]


@pytest.mark.parametrize("word", ["RESET", "yes", "", True, 1])
def test_any_other_word_gets_a_refusal_and_deletes_nothing(app, environment, word):
    with session_client(app) as client:
        response = post(client, confirm=word)
    assert (response.status_code, attempts(environment)) in {(409, 6), (422, 6)}


def test_the_word_resets_and_says_what_went(app, environment, tmp_path):
    with session_client(app) as client:
        document = post(client, confirm="reset").json()
    assert (
        document["deleted"][0],
        attempts(environment),
        (tmp_path / RUN_FILE).exists(),
    ) == ({"label": "attempts", "count": 6}, 0, False)


def test_practice_files_stay_without_the_option(app, tmp_path):
    with session_client(app) as client:
        post(client, confirm="reset")
    assert (tmp_path / PRACTICE_FILE).exists()


def test_files_deletes_practice_files_and_keeps_the_archive(app, tmp_path):
    with session_client(app) as client:
        post(client, confirm="reset", files=True)
    assert ((tmp_path / PRACTICE_FILE).exists(), (tmp_path / ARCHIVED).exists()) == (False, True)


def test_archive_deletes_the_archive(app, tmp_path):
    with session_client(app) as client:
        post(client, confirm="reset", archive=True)
    assert not (tmp_path / ARCHIVED).exists()


def test_an_option_of_another_type_gets_422_and_deletes_nothing(app, environment):
    with session_client(app) as client:
        response = post(client, confirm="reset", files="yes")
    assert (response.status_code, attempts(environment)) == (422, 6)


def test_a_body_that_is_not_an_object_gets_422(app, environment):
    with session_client(app) as client:
        response = client.post(RESET, json=["reset"], headers=WRITE_HEADERS)
    assert (response.status_code, attempts(environment)) == (422, 6)


def test_a_running_child_refuses_it_and_names_the_run(tmp_path):
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
        refused = post(client, confirm="reset")
        busy = client.get(RESET).json()["busy"]
        gate.write_text("")
    assert (
        started.status_code,
        refused.status_code,
        refused.json()["error"]["run"],
        attempts(environment),
        busy is not None,
    ) == (201, 409, started.json()["id"], 1, True)


SETS_FILE = "sets:\n  backend-loop:\n    problems:\n      - two-sum\n"


def test_the_preview_says_sets_stay(app):
    with session_client(app) as client:
        assert any("sets.yaml" in kept for kept in client.get(RESET).json()["kept"])


@pytest.mark.parametrize(
    "options",
    [{}, {"files": True}, {"archive": True}, {"files": True, "archive": True}],
    ids=["plain", "files", "archive", "files and archive"],
)
def test_sets_survive_every_reset(app, tmp_path, options):
    file = tmp_path / "sets.yaml"
    file.write_text(SETS_FILE)
    with session_client(app) as client:
        response = post(client, confirm="reset", **options)
    assert (response.status_code, file.read_text()) == (200, SETS_FILE)
