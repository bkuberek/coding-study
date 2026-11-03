"""The files of a past attempt, read-only (docs/specs/web-ui.md#past-attempt-files): the listing
with its source, one file, the limits of the file API, and the security model of every endpoint."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from coding_study.application.attempt_files import EDITABLE_BYTES
from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import Attempt
from coding_study.domain.problem import Language
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.web_server import (
    PORT,
    WRITE_HEADERS,
    anonymous_client,
    session_client,
    web_app,
)

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUB = "python/practice/two_sum.py"
SOLVED = "def two_sum(): return [0, 1]\n"


@pytest.fixture
def practice(tmp_path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    return make_environment(root, toolchains=toolchains)


@pytest.fixture
def client(tmp_path, practice) -> Iterator[TestClient]:
    with session_client(web_app(tmp_path, practice)) as session:
        yield session


def start(practice: Environment) -> Attempt:
    return start_attempt(practice, StartRequest("two-sum", Language.PYTHON)).attempt


def finish(practice: Environment, text: str = SOLVED) -> Attempt:
    """An attempt whose file holds `text`, finished with Done."""
    attempt = start(practice)
    practice.workspace.write_text(STUB, text)
    complete_attempt(practice, DoneRequest(gave_up=True))
    return attempt


def listing(attempt: Attempt) -> str:
    return f"/api/v1/attempts/{attempt.id}/past-files"


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


# the listing


def test_the_latest_attempts_listing_is_its_current_files(client, practice):
    attempt = finish(practice)
    assert client.get(listing(attempt)).json() == {
        "source": "current",
        "root": "python/practice",
        "entries": [{"path": "two_sum.py", "size": len(SOLVED)}],
    }


def test_an_older_attempts_listing_is_its_archive(client, practice):
    attempt = finish(practice)
    start(practice)
    assert client.get(listing(attempt)).json() == {
        "source": "archive",
        "root": f".archive/two-sum/{attempt.id}-python",
        "entries": [{"path": "two_sum.py", "size": len(SOLVED)}],
    }


def test_the_listing_of_an_attempt_without_files_says_missing(client, practice):
    attempt = finish(practice)
    practice.workspace.absolute(STUB).unlink()
    assert client.get(listing(attempt)).json() == {"source": "missing", "root": None, "entries": []}


def test_an_attempt_in_progress_gets_422_pointing_to_the_attempt_view(client, practice):
    attempt = start(practice)
    response = client.get(listing(attempt))
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        f"attempt {attempt.id} of two-sum is in progress; open it in the Attempt view",
    )


def test_an_unknown_attempt_gets_404_not_found(client):
    response = client.get("/api/v1/attempts/41/past-files")
    assert (error(response), response.json()["error"]["message"]) == (
        (404, "not_found"),
        "unknown attempt 41",
    )


def test_an_attempt_id_that_is_not_a_number_gets_404(client):
    assert error(client.get("/api/v1/attempts/two-sum/past-files")) == (404, "not_found")


# one file


def test_a_file_reads_as_its_document(client, practice):
    attempt = finish(practice)
    start(practice)
    response = client.get(f"{listing(attempt)}/two_sum.py")
    assert response.json() == {
        "path": "two_sum.py",
        "source": "archive",
        "size": len(SOLVED),
        "text": SOLVED,
    }


def test_a_current_file_reads_as_it_is_now(client, practice):
    attempt = finish(practice)
    practice.workspace.write_text(STUB, "edited since\n")
    document = client.get(f"{listing(attempt)}/two_sum.py").json()
    assert (document["source"], document["text"]) == ("current", "edited since\n")


def test_text_over_1_mib_reads_without_its_text(client, practice):
    attempt = finish(practice, "a" * (EDITABLE_BYTES + 1))
    document = client.get(f"{listing(attempt)}/two_sum.py").json()
    assert (document["text"], document["size"]) == (None, EDITABLE_BYTES + 1)


def test_a_file_that_is_not_utf8_reads_without_its_text(client, practice):
    attempt = finish(practice)
    start(practice)
    folder = practice.workspace.absolute(f".archive/two-sum/{attempt.id}-python")
    (folder / "data.bin").write_bytes(b"\xff\xfe\x00")
    assert client.get(f"{listing(attempt)}/data.bin").json()["text"] is None


def test_a_path_that_leaves_the_archive_gets_422_usage(client, practice):
    attempt = finish(practice)
    start(practice)
    response = client.get(f"{listing(attempt)}/%2E%2E/%2E%2E/%2E%2E/progress.db")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "cannot read ../../../progress.db: leaves the folder",
    )


def test_a_path_that_leaves_the_current_root_gets_422_usage(client, practice):
    attempt = finish(practice)
    response = client.get(f"{listing(attempt)}/%2E%2E/practice/two_sum.py")
    assert error(response) == (422, "usage")


def test_an_absolute_path_gets_422_usage(client, practice):
    attempt = finish(practice)
    start(practice)
    assert error(client.get(f"{listing(attempt)}//etc/hosts")) == (422, "usage")


def test_a_link_in_the_archive_gets_422_and_is_not_followed(client, practice, tmp_path):
    attempt = finish(practice)
    start(practice)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n")
    folder = practice.workspace.absolute(f".archive/two-sum/{attempt.id}-python")
    (folder / "link.txt").symlink_to(outside)
    response = client.get(f"{listing(attempt)}/link.txt")
    assert (error(response), "secret" in response.text) == ((422, "usage"), False)


def test_a_file_the_files_lack_gets_404_not_found(client, practice):
    attempt = finish(practice)
    start(practice)
    response = client.get(f"{listing(attempt)}/other.py")
    assert (error(response), response.json()["error"]["message"]) == (
        (404, "not_found"),
        f"no file other.py in .archive/two-sum/{attempt.id}-python",
    )


def test_a_file_of_an_attempt_without_files_gets_404_not_found(client, practice):
    attempt = finish(practice)
    practice.workspace.absolute(STUB).unlink()
    assert error(client.get(f"{listing(attempt)}/two_sum.py")) == (404, "not_found")


def test_a_file_of_an_attempt_in_progress_gets_422(client, practice):
    attempt = start(practice)
    assert error(client.get(f"{listing(attempt)}/two_sum.py")) == (422, "usage")


# security: as every endpoint


def test_the_listing_needs_the_session_cookie(tmp_path, practice):
    attempt = finish(practice)
    with anonymous_client(web_app(tmp_path, practice)) as anonymous:
        assert error(anonymous.get(listing(attempt))) == (401, "unauthorized")


def test_a_file_needs_the_session_cookie(tmp_path, practice):
    attempt = finish(practice)
    with anonymous_client(web_app(tmp_path, practice)) as anonymous:
        assert error(anonymous.get(f"{listing(attempt)}/two_sum.py")) == (401, "unauthorized")


def test_the_listing_of_another_host_gets_403_forbidden(client, practice):
    attempt = finish(practice)
    response = client.get(listing(attempt), headers={"Host": f"rebound.example:{PORT}"})
    assert error(response) == (403, "forbidden")


def test_a_file_of_another_host_gets_403_forbidden(client, practice):
    attempt = finish(practice)
    response = client.get(
        f"{listing(attempt)}/two_sum.py", headers={"Host": f"rebound.example:{PORT}"}
    )
    assert error(response) == (403, "forbidden")


def test_the_listing_is_never_stored(client, practice):
    attempt = finish(practice)
    assert client.get(listing(attempt)).headers["cache-control"] == "no-store"


def test_a_file_is_never_stored(client, practice):
    attempt = finish(practice)
    assert client.get(f"{listing(attempt)}/two_sum.py").headers["cache-control"] == "no-store"


def test_a_refusal_is_never_stored(client):
    assert client.get("/api/v1/attempts/41/past-files").headers["cache-control"] == "no-store"


@pytest.mark.parametrize("method", ["PUT", "POST", "DELETE", "PATCH"])
def test_the_files_take_no_write(client, practice, method):
    attempt = finish(practice)
    response = client.request(method, f"{listing(attempt)}/two_sum.py", headers=WRITE_HEADERS)
    assert error(response) == (405, "method_not_allowed")


@pytest.mark.parametrize("method", ["PUT", "POST", "DELETE", "PATCH"])
def test_the_listing_takes_no_write(client, practice, method):
    attempt = finish(practice)
    response = client.request(method, listing(attempt), headers=WRITE_HEADERS)
    assert error(response) == (405, "method_not_allowed")


def test_a_write_never_changes_the_file(client, practice):
    attempt = finish(practice)
    client.put(f"{listing(attempt)}/two_sum.py", json={"text": "x\n"}, headers=WRITE_HEADERS)
    assert practice.workspace.read_text(STUB) == SOLVED
