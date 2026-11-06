"""Changing an attempt's files from the page: save, create, move, delete and restore
(docs/specs/web-ui.md#attempts, docs/specs/web-ui.md#file-api-rules)."""

import hashlib
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from starlette.testclient import TestClient
from starlette.types import ASGIApp

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.toml_config_file import TomlConfigFile
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.problem import Language
from coding_study.domain.project_manifest import project_lock
from coding_study.entrypoints.web.app import create_app
from coding_study.entrypoints.web.context import ServerSettings
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.racing_workspace import OutsideDeletion
from tests.web_server import (
    PORT,
    SECRETS,
    TEST_VERSION,
    WRITE_HEADERS,
    session_client,
    static_directory,
    web_app,
)

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
STUB_TEXT = "# stub for two-sum\n"
PROJECT = f"projects/{PROJECT_SLUG}"
README = "# Bank Project (Python)"
SAVED = "class Bank:\n    pass\n"
SHORT_DEADLINE_S = 0.05


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


@pytest.fixture
def client(tmp_path, project) -> Iterator[TestClient]:
    with session_client(web_app(tmp_path, project)) as session:
        yield session


@pytest.fixture
def practice_client(tmp_path, practice) -> Iterator[TestClient]:
    with session_client(web_app(tmp_path, practice)) as session:
        yield session


def impatient_app(root: Path, environment: Environment) -> ASGIApp:
    """The app of a server that waits only `SHORT_DEADLINE_S` for a project's lock."""
    return create_app(
        ServerSettings(
            port=PORT,
            version=TEST_VERSION,
            secrets=SECRETS,
            static_directory=static_directory(root),
            load_environment=lambda: environment,
            preferences=FsPreferencesStore(root),
            config_file=TomlConfigFile(root / "config.toml"),
            lock_deadline_s=SHORT_DEADLINE_S,
        )
    )


def file_url(attempt: Attempt, path: str) -> str:
    return f"/api/v1/attempts/{attempt.id}/files/{path}"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def etag(environment: Environment, path: str) -> str:
    """The ETag a read of the file in the workspace gives."""
    return f'"{hashlib.sha256(environment.workspace.absolute(path).read_bytes()).hexdigest()}"'


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def save(client: TestClient, url: str, text: str, if_match: str):
    return client.put(url, json={"text": text}, headers={**WRITE_HEADERS, "If-Match": if_match})


def create(client: TestClient, url: str, text: str):
    return client.put(url, json={"text": text}, headers={**WRITE_HEADERS, "If-None-Match": "*"})


# saving


def test_a_save_with_the_files_etag_answers_its_path_and_sha256(client, project, project_attempt):
    url = file_url(project_attempt, "bank/bank.py")
    response = save(client, url, SAVED, etag(project, f"{PROJECT}/bank/bank.py"))
    assert (response.status_code, response.json()) == (
        200,
        {"path": "bank/bank.py", "sha256": sha(SAVED)},
    )


def test_a_save_writes_the_text(client, project, project_attempt):
    url = file_url(project_attempt, "bank/bank.py")
    save(client, url, SAVED, etag(project, f"{PROJECT}/bank/bank.py"))
    assert project.workspace.read_text(f"{PROJECT}/bank/bank.py") == SAVED


def test_a_saves_etag_is_the_new_sha256(client, project, project_attempt):
    url = file_url(project_attempt, "bank/bank.py")
    response = save(client, url, SAVED, etag(project, f"{PROJECT}/bank/bank.py"))
    assert response.headers["etag"] == f'"{sha(SAVED)}"'


def test_a_saved_file_reads_as_modified(client, project, project_attempt):
    url = file_url(project_attempt, "bank/bank.py")
    save(client, url, SAVED, etag(project, f"{PROJECT}/bank/bank.py"))
    assert client.get(url).json()["state"] == "modified"


def test_a_stale_if_match_gets_412_precondition_failed(client, project, project_attempt):
    stale = etag(project, f"{PROJECT}/README.md")
    project.workspace.write_text(f"{PROJECT}/README.md", "# Theirs\n")
    response = save(client, file_url(project_attempt, "README.md"), "# Mine\n", stale)
    assert error(response) == (412, "precondition_failed")


def test_a_412_names_the_sha256_of_the_files_content_now(client, project, project_attempt):
    stale = etag(project, f"{PROJECT}/README.md")
    project.workspace.write_text(f"{PROJECT}/README.md", "# Theirs\n")
    response = save(client, file_url(project_attempt, "README.md"), "# Mine\n", stale)
    assert response.json()["error"]["sha256"] == sha("# Theirs\n")


def test_a_412_carries_the_files_etag_now(client, project, project_attempt):
    stale = etag(project, f"{PROJECT}/README.md")
    project.workspace.write_text(f"{PROJECT}/README.md", "# Theirs\n")
    response = save(client, file_url(project_attempt, "README.md"), "# Mine\n", stale)
    assert response.headers["etag"] == f'"{sha("# Theirs\n")}"'


def test_a_save_of_a_file_deleted_since_gets_412_without_a_sha256(client, project, project_attempt):
    stale = etag(project, f"{PROJECT}/README.md")
    project.workspace.absolute(f"{PROJECT}/README.md").unlink()
    response = save(client, file_url(project_attempt, "README.md"), "# Mine\n", stale)
    assert (error(response), response.json()["error"]["sha256"]) == (
        (412, "precondition_failed"),
        None,
    )


def test_a_save_without_if_match_gets_428_precondition_required(client, project_attempt):
    response = client.put(
        file_url(project_attempt, "README.md"), json={"text": "# Mine\n"}, headers=WRITE_HEADERS
    )
    assert error(response) == (428, "precondition_required")


def test_a_save_without_the_csrf_header_gets_403(client, project, project_attempt):
    response = client.put(
        file_url(project_attempt, "README.md"),
        json={"text": "# Mine\n"},
        headers={
            "Origin": WRITE_HEADERS["Origin"],
            "If-Match": etag(project, f"{PROJECT}/README.md"),
        },
    )
    assert error(response) == (403, "forbidden")


def test_a_path_that_leaves_the_root_gets_422_usage(client, project_attempt):
    url = file_url(project_attempt, "bank/%2E%2E/%2E%2E/x.py")
    response = save(client, url, SAVED, '"unused"')
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "cannot save bank/../../x.py: leaves the folder",
    )


def test_an_absolute_path_gets_422_usage(client, project_attempt):
    response = save(client, file_url(project_attempt, "%2Fetc/hosts"), SAVED, '"unused"')
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "cannot save /etc/hosts: is absolute: name the file relative to the project folder",
    )


def test_a_backslash_path_gets_422_usage(client, project_attempt):
    response = save(client, file_url(project_attempt, "bank%5Cbank.py"), SAVED, '"unused"')
    assert error(response) == (422, "usage")


def test_a_save_through_a_link_gets_422_and_leaves_its_target_alone(
    client, project, project_attempt
):
    project.workspace.write_text("secret.txt", "secret\n")
    project.workspace.absolute(f"{PROJECT}/README.md").unlink()
    project.workspace.absolute(f"{PROJECT}/README.md").symlink_to("../../secret.txt")
    response = save(
        client, file_url(project_attempt, "README.md"), "# Mine\n", f'"{sha("secret\n")}"'
    )
    assert (error(response), project.workspace.read_text("secret.txt")) == (
        (422, "usage"),
        "secret\n",
    )


def test_a_save_under_a_directory_that_is_a_link_gets_422(client, project, project_attempt):
    project.workspace.write_text("elsewhere/bank.py", "kept\n")
    project.workspace.remove_folder(f"{PROJECT}/bank")
    project.workspace.absolute(f"{PROJECT}/bank").symlink_to(
        "../../elsewhere", target_is_directory=True
    )
    response = save(client, file_url(project_attempt, "bank/bank.py"), SAVED, f'"{sha("kept\n")}"')
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "cannot save bank/bank.py: bank is a symbolic link",
    )


def test_a_file_a_tool_wrote_gets_422(client, project_attempt):
    response = save(client, file_url(project_attempt, ".venv/bin/python"), SAVED, '"unused"')
    assert error(response) == (422, "usage")


def test_text_over_1_mib_gets_413_too_large(client, project, project_attempt):
    url = file_url(project_attempt, "README.md")
    response = save(client, url, "#" * (1024 * 1024 + 1), etag(project, f"{PROJECT}/README.md"))
    assert error(response) == (413, "too_large")


def test_a_body_without_text_gets_422_usage(client, project, project_attempt):
    response = client.put(
        file_url(project_attempt, "README.md"),
        json={"content": "# Mine\n"},
        headers={**WRITE_HEADERS, "If-Match": etag(project, f"{PROJECT}/README.md")},
    )
    assert error(response) == (422, "usage")


def test_a_save_while_the_projects_lock_stays_busy_gets_409_locked(
    tmp_path, project, project_attempt
):
    with (
        session_client(impatient_app(tmp_path, project)) as client,
        exclusive_lock(project.workspace.absolute(project_lock(PROJECT_SLUG))),
    ):
        url = file_url(project_attempt, "README.md")
        response = save(client, url, "# Mine\n", etag(project, f"{PROJECT}/README.md"))
    assert error(response) == (409, "locked")


def test_a_save_for_an_ended_attempt_gets_409_attempt_ended(client, project, project_attempt):
    project.progress.update_attempt(replace(project_attempt, status=AttemptStatus.ABANDONED))
    url = file_url(project_attempt, "README.md")
    response = save(client, url, "# Mine\n", etag(project, f"{PROJECT}/README.md"))
    assert error(response) == (409, "attempt_ended")


def test_a_single_file_attempts_file_saves(practice_client, practice, python_attempt):
    url = file_url(python_attempt, "two_sum.py")
    response = save(practice_client, url, SAVED, f'"{sha(STUB_TEXT)}"')
    assert (response.status_code, practice.workspace.read_text("python/practice/two_sum.py")) == (
        200,
        SAVED,
    )


# creating


def test_creating_with_if_none_match_star_gets_201(client, project_attempt):
    response = create(client, file_url(project_attempt, "bank/ledger.py"), "LEDGER = []\n")
    assert (response.status_code, response.json()) == (
        201,
        {"path": "bank/ledger.py", "sha256": sha("LEDGER = []\n")},
    )


def test_a_created_file_reads_as_added(client, project_attempt):
    url = file_url(project_attempt, "bank/ledger.py")
    create(client, url, "LEDGER = []\n")
    assert client.get(url).json()["state"] == "added"


def test_creating_a_file_that_exists_gets_412_with_its_sha256(client, project, project_attempt):
    response = create(client, file_url(project_attempt, "README.md"), "# Mine\n")
    assert (error(response), f'"{response.json()["error"]["sha256"]}"') == (
        (412, "precondition_failed"),
        etag(project, f"{PROJECT}/README.md"),
    )


def test_creating_beside_a_single_file_attempts_file_gets_422(practice_client, python_attempt):
    response = create(practice_client, file_url(python_attempt, "helper.py"), "x = 1\n")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "cannot create helper.py: the attempt has one file, two_sum.py",
    )


def test_a_method_a_file_does_not_take_gets_405_naming_the_ones_it_takes(client, project_attempt):
    response = client.patch(file_url(project_attempt, "README.md"), headers=WRITE_HEADERS)
    allowed = {method.strip() for method in response.headers["allow"].split(",")}
    assert (error(response), allowed) == (
        (405, "method_not_allowed"),
        {"GET", "HEAD", "PUT", "DELETE"},
    )


# moving


def move(client: TestClient, attempt: Attempt, path: str, to: str, if_match: str):
    return client.post(
        f"{file_url(attempt, path)}/move",
        json={"to": to},
        headers={**WRITE_HEADERS, "If-Match": if_match},
    )


def test_a_move_answers_the_new_path_and_the_files_sha256(client, project, project_attempt):
    expected = etag(project, f"{PROJECT}/README.md")
    response = move(client, project_attempt, "README.md", "docs/README.md", expected)
    assert (response.status_code, response.json()) == (
        200,
        {"path": "docs/README.md", "sha256": expected.strip('"')},
    )


def test_a_moved_file_reads_at_its_new_path(client, project, project_attempt):
    move(client, project_attempt, "README.md", "NOTES.md", etag(project, f"{PROJECT}/README.md"))
    assert client.get(file_url(project_attempt, "NOTES.md")).json()["state"] == "added"


def test_a_move_onto_a_file_gets_409_conflict(client, project, project_attempt):
    expected = etag(project, f"{PROJECT}/README.md")
    response = move(client, project_attempt, "README.md", "bank/bank.py", expected)
    assert error(response) == (409, "conflict")


def test_a_move_with_a_stale_if_match_gets_412(client, project, project_attempt):
    stale = etag(project, f"{PROJECT}/README.md")
    project.workspace.write_text(f"{PROJECT}/README.md", "# Theirs\n")
    response = move(client, project_attempt, "README.md", "NOTES.md", stale)
    assert error(response) == (412, "precondition_failed")


@pytest.fixture
def racing_client(tmp_path, project) -> Iterator[TestClient]:
    """A server whose moves and deletes find their file deleted by another program."""
    racing = replace(project, workspace=OutsideDeletion(project.root))
    with session_client(web_app(tmp_path, racing)) as session:
        yield session


def test_a_move_of_a_file_deleted_on_the_way_gets_412_without_a_sha256(
    racing_client, project, project_attempt
):
    expected = etag(project, f"{PROJECT}/README.md")
    response = move(racing_client, project_attempt, "README.md", "NOTES.md", expected)
    assert (*error(response), response.json()["error"]["sha256"]) == (
        412,
        "precondition_failed",
        None,
    )


def test_a_move_without_if_match_gets_428(client, project_attempt):
    response = client.post(
        f"{file_url(project_attempt, 'README.md')}/move",
        json={"to": "NOTES.md"},
        headers=WRITE_HEADERS,
    )
    assert error(response) == (428, "precondition_required")


@pytest.mark.parametrize("target", ["../README.md", "/etc/README.md", "bank\\README.md"])
def test_a_move_out_of_the_root_gets_422(client, project, project_attempt, target):
    expected = etag(project, f"{PROJECT}/README.md")
    response = move(client, project_attempt, "README.md", target, expected)
    assert error(response) == (422, "usage")


def test_a_move_without_a_target_gets_422(client, project, project_attempt):
    response = client.post(
        f"{file_url(project_attempt, 'README.md')}/move",
        json={},
        headers={**WRITE_HEADERS, "If-Match": etag(project, f"{PROJECT}/README.md")},
    )
    assert error(response) == (422, "usage")


def test_a_move_in_a_single_file_attempt_gets_422(practice_client, python_attempt):
    response = move(practice_client, python_attempt, "two_sum.py", "x.py", f'"{sha(STUB_TEXT)}"')
    assert error(response) == (422, "usage")


# deleting


def delete(client: TestClient, attempt: Attempt, path: str, if_match: str):
    return client.delete(file_url(attempt, path), headers={**WRITE_HEADERS, "If-Match": if_match})


def test_a_delete_gets_204(client, project, project_attempt):
    response = delete(client, project_attempt, "README.md", etag(project, f"{PROJECT}/README.md"))
    assert (response.status_code, response.content) == (204, b"")


def test_a_deleted_starter_file_shows_deleted_in_the_tree(client, project, project_attempt):
    delete(client, project_attempt, "README.md", etag(project, f"{PROJECT}/README.md"))
    entries = client.get(f"/api/v1/attempts/{project_attempt.id}/files").json()["entries"]
    assert next(entry["state"] for entry in entries if entry["path"] == "README.md") == "deleted"


def test_a_delete_without_if_match_gets_428(client, project_attempt):
    response = client.delete(file_url(project_attempt, "README.md"), headers=WRITE_HEADERS)
    assert error(response) == (428, "precondition_required")


def test_a_delete_with_a_stale_if_match_gets_412(client, project, project_attempt):
    stale = etag(project, f"{PROJECT}/README.md")
    project.workspace.write_text(f"{PROJECT}/README.md", "# Theirs\n")
    response = delete(client, project_attempt, "README.md", stale)
    assert error(response) == (412, "precondition_failed")


def test_a_delete_of_a_file_deleted_on_the_way_gets_412_without_a_sha256(
    racing_client, project, project_attempt
):
    expected = etag(project, f"{PROJECT}/README.md")
    response = delete(racing_client, project_attempt, "README.md", expected)
    assert (*error(response), response.json()["error"]["sha256"]) == (
        412,
        "precondition_failed",
        None,
    )


def test_a_delete_through_a_link_gets_422(client, project, project_attempt):
    project.workspace.write_text("secret.txt", "secret\n")
    project.workspace.absolute(f"{PROJECT}/README.md").unlink()
    project.workspace.absolute(f"{PROJECT}/README.md").symlink_to("../../secret.txt")
    response = delete(client, project_attempt, "README.md", f'"{sha("secret\n")}"')
    assert error(response) == (422, "usage")


def test_a_delete_that_leaves_the_root_gets_422(client, project_attempt):
    response = delete(client, project_attempt, "bank/%2E%2E/%2E%2E/x.py", '"unused"')
    assert error(response) == (422, "usage")


def test_a_delete_while_the_projects_lock_stays_busy_gets_409_locked(
    tmp_path, project, project_attempt
):
    with (
        session_client(impatient_app(tmp_path, project)) as client,
        exclusive_lock(project.workspace.absolute(project_lock(PROJECT_SLUG))),
    ):
        expected = etag(project, f"{PROJECT}/README.md")
        response = delete(client, project_attempt, "README.md", expected)
    assert error(response) == (409, "locked")


# restoring


def restore(client: TestClient, attempt: Attempt, path: str):
    return client.post(
        f"/api/v1/attempts/{attempt.id}/restore", json={"path": path}, headers=WRITE_HEADERS
    )


def test_a_restore_answers_the_files_path_origin_and_level(client, project, project_attempt):
    project.workspace.write_text(f"{PROJECT}/README.md", "# Mine\n")
    response = restore(client, project_attempt, "README.md")
    assert (response.status_code, response.json()) == (
        200,
        {"path": "README.md", "origin": "starter", "level": None},
    )


def test_a_restored_file_reads_as_unchanged(client, project, project_attempt):
    project.workspace.write_text(f"{PROJECT}/README.md", "# Mine\n")
    restore(client, project_attempt, "README.md")
    assert client.get(file_url(project_attempt, "README.md")).json()["state"] == "unchanged"


def test_restoring_a_generated_test_file_names_its_level(client, project, project_attempt):
    test_file = next(
        entry["path"]
        for entry in client.get(f"/api/v1/attempts/{project_attempt.id}/files").json()["entries"]
        if entry["origin"] == "level"
    )
    project.workspace.absolute(f"{PROJECT}/{test_file}").unlink()
    response = restore(client, project_attempt, test_file)
    assert (response.json()["origin"], response.json()["level"]) == ("level", 1)


def test_restoring_a_file_you_added_gets_422_with_the_clis_message(
    client, project, project_attempt
):
    project.workspace.write_text(f"{PROJECT}/bank/ledger.py", "LEDGER = []\n")
    response = restore(client, project_attempt, "bank/ledger.py")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "cannot restore bank/ledger.py: not a starter file or a generated test file of an open "
        f"level of {PROJECT_SLUG}",
    )


def test_restoring_in_a_single_file_attempt_gets_422(practice_client, python_attempt):
    response = restore(practice_client, python_attempt, "two_sum.py")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "--restore is for project problems",
    )


def test_a_restore_without_a_path_gets_422(client, project_attempt):
    response = client.post(
        f"/api/v1/attempts/{project_attempt.id}/restore", json={}, headers=WRITE_HEADERS
    )
    assert error(response) == (422, "usage")


def test_a_restore_while_the_projects_lock_stays_busy_gets_409_locked(
    tmp_path, project, project_attempt
):
    with (
        session_client(impatient_app(tmp_path, project)) as client,
        exclusive_lock(project.workspace.absolute(project_lock(PROJECT_SLUG))),
    ):
        response = restore(client, project_attempt, "README.md")
    assert error(response) == (409, "locked")


def test_a_restore_for_an_ended_attempt_gets_409(client, project, project_attempt):
    project.progress.update_attempt(replace(project_attempt, status=AttemptStatus.ABANDONED))
    assert error(restore(client, project_attempt, "README.md")) == (409, "attempt_ended")
