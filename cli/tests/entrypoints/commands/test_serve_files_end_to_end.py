"""Changing a project's files through a real `cstudy serve`, each state checked against what
`cstudy status --json` prints for the same workspace: save a starter file, see it `modified`,
restore it as `cstudy start --restore` does, see it `unchanged`
(docs/specs/web-ui.md#file-api-rules)."""

import json
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path

import httpx2
import pytest

from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow

PROJECT = "bank-project-python"
FILE = "bank/bank.py"
SAVED = "class Bank:\n    pass\n"
COMMAND_SECONDS = 240


def cstudy(workspace: Path, environment: Mapping[str, str], *arguments: str) -> str:
    finished = subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=environment,
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=COMMAND_SECONDS,
    )
    return finished.stdout


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = mark_workspace(tmp_path_factory.mktemp("files") / "workspace")
    cstudy(root, served_environment(root), "start", PROJECT, "--no-open")
    return root


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def browser(server: RunningServer) -> Iterator[httpx2.Client]:
    with httpx2.Client(base_url=server.address, timeout=COMMAND_SECONDS) as client:
        client.get(server.login_url)
        yield client


@pytest.fixture(scope="module")
def write_headers(server: RunningServer, browser: httpx2.Client) -> dict[str, str]:
    page = browser.get("/").text
    csrf = page.split('<meta name="cstudy-csrf" content="')[1].split('"')[0]
    return {"Origin": server.address, "X-Cstudy-CSRF": csrf}


@pytest.fixture(scope="module")
def attempt(browser: httpx2.Client) -> int:
    entries = browser.get("/api/v1/problems").json()["entries"]
    return next(
        entry["in_progress"][0]["attempt_id"] for entry in entries if entry["slug"] == PROJECT
    )


@pytest.fixture(scope="module")
def states(workspace: Path, server: RunningServer):
    """The state `cstudy status --json` prints for `FILE` in the server's workspace."""

    def state() -> str:
        document = json.loads(cstudy(workspace, server.environment, "status", PROJECT, "--json"))
        return next(
            entry["state"] for entry in document["files"]["entries"] if entry["path"] == FILE
        )

    return state


@pytest.fixture(scope="module")
def saved(browser, write_headers, attempt) -> httpx2.Response:
    """The file opened in the page, edited and saved with the ETag its read gave."""
    url = f"/api/v1/attempts/{attempt}/files/{FILE}"
    etag = browser.get(url).headers["etag"]
    return browser.put(url, json={"text": SAVED}, headers={**write_headers, "If-Match": etag})


@pytest.fixture(scope="module")
def restored(saved, browser, write_headers, attempt) -> httpx2.Response:
    """The saved file restored, as `cstudy start --restore` would."""
    restore = f"/api/v1/attempts/{attempt}/restore"
    return browser.post(restore, json={"path": FILE}, headers=write_headers)


def test_a_save_answers_200(saved):
    assert saved.status_code == 200


def test_a_saved_file_is_on_disk(saved, workspace):
    assert (workspace / "projects" / PROJECT / FILE).read_text() == SAVED


def test_a_saved_starter_file_reads_as_modified(saved, browser, attempt):
    tree = browser.get(f"/api/v1/attempts/{attempt}/files").json()["entries"]
    assert next(entry["state"] for entry in tree if entry["path"] == FILE) == "modified"


def test_cstudy_status_agrees_the_saved_file_is_modified(saved, states):
    assert states() == "modified"


def test_a_save_with_the_old_etag_gets_412(saved, browser, write_headers, attempt):
    url = f"/api/v1/attempts/{attempt}/files/{FILE}"
    stale = {**write_headers, "If-Match": '"0"'}
    assert browser.put(url, json={"text": "x\n"}, headers=stale).status_code == 412


def test_a_restore_answers_the_starter_origin(restored):
    assert (restored.status_code, restored.json()) == (
        200,
        {"path": FILE, "origin": "starter", "level": None},
    )


def test_a_restored_file_reads_as_unchanged(restored, browser, attempt):
    tree = browser.get(f"/api/v1/attempts/{attempt}/files").json()["entries"]
    assert next(entry["state"] for entry in tree if entry["path"] == FILE) == "unchanged"


def test_cstudy_status_agrees_the_restored_file_is_unchanged(restored, states):
    assert states() == "unchanged"
