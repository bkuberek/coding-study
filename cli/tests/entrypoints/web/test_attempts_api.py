"""An attempt's status, its file tree and its files (docs/specs/web-ui.md#attempts,
docs/specs/web-ui.md#file-api-rules)."""

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.attempt_status import attempt_status
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.problem import Language
from coding_study.entrypoints.commands.status import status_document
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.web_server import session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
STUB_TEXT = "# stub for two-sum\n"
PROJECT = f"projects/{PROJECT_SLUG}"


@pytest.fixture
def practice(tmp_path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    return make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))


@pytest.fixture
def project(tmp_path) -> Environment:
    return project_environment(tmp_path, ScriptedProjectProcess())


@pytest.fixture
def python_attempt(practice) -> Attempt:
    return start_attempt(practice, StartRequest("two-sum", Language.PYTHON)).attempt


@pytest.fixture
def project_attempt(project) -> Attempt:
    return start_attempt(project, StartRequest(PROJECT_SLUG)).attempt


def get(tmp_path: Path, environment: Environment, path: str):
    with session_client(web_app(tmp_path, environment)) as client:
        return client.get(path)


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def expected_status(environment: Environment, attempt: Attempt):
    return status_document(attempt_status(environment, attempt.slug, attempt.language))


# status


def test_an_attempts_status_is_its_status_document(tmp_path, practice, python_attempt):
    response = get(tmp_path, practice, f"/api/v1/attempts/{python_attempt.id}")
    assert response.json() == expected_status(practice, python_attempt)


def test_a_project_attempts_status_is_its_status_document(tmp_path, project, project_attempt):
    response = get(tmp_path, project, f"/api/v1/attempts/{project_attempt.id}")
    assert response.json() == expected_status(project, project_attempt)


def test_an_items_status_is_its_status_document(tmp_path, practice):
    attempt = start_item_attempt(practice, ItemStartRequest("url-shortener")).attempt
    response = get(tmp_path, practice, f"/api/v1/attempts/{attempt.id}")
    assert response.json() == expected_status(practice, attempt)


def test_an_unknown_attempt_gets_404_not_found(tmp_path, practice):
    response = get(tmp_path, practice, "/api/v1/attempts/41")
    assert (error(response), response.json()["error"]["message"]) == (
        (404, "not_found"),
        "unknown attempt 41",
    )


def test_a_finished_attempt_gets_409_attempt_ended(tmp_path, practice, python_attempt):
    practice.progress.update_attempt(replace(python_attempt, status=AttemptStatus.PASSED))
    response = get(tmp_path, practice, f"/api/v1/attempts/{python_attempt.id}")
    assert (error(response), response.json()["error"]["message"]) == (
        (409, "attempt_ended"),
        f"attempt {python_attempt.id} of two-sum is no longer in progress",
    )


def test_an_attempt_a_fresh_start_replaced_gets_409_attempt_ended(
    tmp_path, practice, python_attempt
):
    start_attempt(practice, StartRequest("two-sum", Language.PYTHON, fresh=True))
    response = get(tmp_path, practice, f"/api/v1/attempts/{python_attempt.id}")
    assert error(response) == (409, "attempt_ended")


def test_an_attempt_id_that_is_not_a_number_gets_404(tmp_path, practice):
    assert error(get(tmp_path, practice, "/api/v1/attempts/two-sum")) == (404, "not_found")


# the tree


def test_a_single_file_attempts_tree_is_its_file(tmp_path, practice, python_attempt):
    response = get(tmp_path, practice, f"/api/v1/attempts/{python_attempt.id}/files")
    assert response.json() == {
        "root": "python/practice",
        "entries": [
            {
                "path": "two_sum.py",
                "origin": "stub",
                "level": None,
                "state": None,
                "size": len(STUB_TEXT),
                "editable": True,
            }
        ],
    }


def test_a_projects_tree_is_its_status_entries_with_size_and_editable(
    tmp_path, project, project_attempt
):
    response = get(tmp_path, project, f"/api/v1/attempts/{project_attempt.id}/files")
    entries = expected_status(project, project_attempt)["files"]["entries"]  # type: ignore[index]
    tree = response.json()
    assert [
        {key: entry[key] for key in ("path", "origin", "level", "state")}
        for entry in tree["entries"]
    ] == entries


def test_a_projects_tree_is_rooted_at_its_folder(tmp_path, project, project_attempt):
    response = get(tmp_path, project, f"/api/v1/attempts/{project_attempt.id}/files")
    assert response.json()["root"] == PROJECT


def test_the_tree_of_an_unknown_attempt_gets_404(tmp_path, practice):
    assert error(get(tmp_path, practice, "/api/v1/attempts/41/files")) == (404, "not_found")


# one file


def file_url(attempt: Attempt, path: str) -> str:
    return f"/api/v1/attempts/{attempt.id}/files/{path}"


def test_a_file_reads_as_its_document(tmp_path, practice, python_attempt):
    response = get(tmp_path, practice, file_url(python_attempt, "two_sum.py"))
    assert response.json() == {
        "path": "two_sum.py",
        "text": STUB_TEXT,
        "sha256": hashlib.sha256(STUB_TEXT.encode()).hexdigest(),
        "origin": "stub",
        "level": None,
        "state": None,
        "editable": True,
    }


def test_a_files_etag_is_its_sha256(tmp_path, practice, python_attempt):
    response = get(tmp_path, practice, file_url(python_attempt, "two_sum.py"))
    assert response.headers["etag"] == f'"{hashlib.sha256(STUB_TEXT.encode()).hexdigest()}"'


def test_raw_gives_the_files_bytes(tmp_path, practice, python_attempt):
    response = get(tmp_path, practice, file_url(python_attempt, "two_sum.py") + "?raw")
    assert (response.content, response.headers["content-type"]) == (
        STUB_TEXT.encode(),
        "application/octet-stream",
    )


def test_a_project_file_reads_with_its_origin_and_state(tmp_path, project, project_attempt):
    response = get(tmp_path, project, file_url(project_attempt, "bank/bank.py"))
    document = response.json()
    assert (document["origin"], document["state"]) == ("starter", "unchanged")


def test_a_file_outside_the_scope_gets_422_usage(tmp_path, practice, python_attempt):
    response = get(tmp_path, practice, file_url(python_attempt, "other.py"))
    assert error(response) == (422, "usage")


def test_a_path_that_leaves_the_root_gets_422_usage(tmp_path, project, project_attempt):
    response = get(tmp_path, project, file_url(project_attempt, "bank/%2E%2E/%2E%2E/x.py"))
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "cannot read bank/../../x.py: leaves the folder",
    )


def test_a_missing_file_gets_404_not_found(tmp_path, project, project_attempt):
    response = get(tmp_path, project, file_url(project_attempt, "bank/ledger.py"))
    assert (error(response), response.json()["error"]["message"]) == (
        (404, "not_found"),
        f"no file bank/ledger.py in {PROJECT}",
    )


def test_a_file_of_an_ended_attempt_gets_409(tmp_path, practice, python_attempt):
    practice.progress.update_attempt(replace(python_attempt, status=AttemptStatus.ABANDONED))
    response = get(tmp_path, practice, file_url(python_attempt, "two_sum.py"))
    assert error(response) == (409, "attempt_ended")
