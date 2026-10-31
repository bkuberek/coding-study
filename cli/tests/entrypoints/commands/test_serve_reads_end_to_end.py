"""Every read endpoint of a real `cstudy serve`, against the `--json` document the matching
command prints for the same workspace (docs/specs/web-ui.md#endpoints).

The commands run with the server's own environment, so both see the same tools and caches."""

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
COMMAND_SECONDS = 240
"""Generous for `cstudy doctor`, which handshakes every runner, on a loaded machine."""


def cstudy(workspace: Path, environment: Mapping[str, str], *arguments: str) -> str:
    finished = subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=environment,
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=COMMAND_SECONDS,
    )
    assert finished.returncode in (0, 4), finished.stderr
    return finished.stdout


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = mark_workspace(tmp_path_factory.mktemp("reads") / "workspace")
    environment = served_environment(root)
    cstudy(root, environment, "start", "two-sum", "--lang", "python", "--no-open")
    cstudy(root, environment, "start", PROJECT, "--no-open")
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
def attempts(browser: httpx2.Client) -> dict[str, int]:
    entries = browser.get("/api/v1/problems").json()["entries"]
    return {
        entry["slug"]: entry["in_progress"][0]["attempt_id"]
        for entry in entries
        if entry["in_progress"]
    }


@pytest.fixture(scope="module")
def printed(workspace: Path, server: RunningServer):
    """What a command prints in the server's workspace and environment."""

    def run(*arguments: str) -> str:
        return cstudy(workspace, server.environment, *arguments)

    return run


@pytest.fixture(scope="module")
def document(printed):
    """The `--json` document of a command in the server's workspace and environment."""
    return lambda *arguments: json.loads(printed(*arguments, "--json"))


def test_the_session_and_preferences_are_read(browser):
    paths = ("/api/v1/session", "/api/v1/preferences")
    assert [browser.get(path).status_code for path in paths] == [200, 200]


def test_the_problem_list_is_cstudy_list_json(browser, document):
    assert browser.get("/api/v1/problems").json() == document("list")


def test_a_filtered_list_is_cstudy_list_json_with_the_filters(browser, document):
    response = browser.get("/api/v1/problems?track=practical&kind=project")
    assert response.json() == document("list", "--track", "practical", "--kind", "project")


def test_the_next_pick_is_cstudy_next_json(browser, document):
    assert browser.get("/api/v1/next").json() == document("next")


def test_a_problem_starts_with_its_list_entry(browser, document):
    entry = next(found for found in document("list")["entries"] if found["slug"] == "two-sum")
    served = browser.get("/api/v1/problems/two-sum").json()
    assert {key: served[key] for key in entry if key != "languages"} == {
        key: value for key, value in entry.items() if key != "languages"
    }


def test_the_statement_is_what_cstudy_show_prints(browser, printed):
    markdown = browser.get("/api/v1/problems/two-sum/statement").json()["markdown"]
    assert markdown == printed("show", "two-sum")


def test_the_history_is_cstudy_history_json(browser, document):
    served = browser.get("/api/v1/problems/two-sum/history").json()
    assert served == document("history", "two-sum")


def test_an_attempts_status_is_cstudy_status_json(browser, attempts, document):
    served = browser.get(f"/api/v1/attempts/{attempts['two-sum']}").json()
    assert served == document("status", "two-sum")


def test_a_projects_status_is_cstudy_status_json(browser, attempts, document):
    served = browser.get(f"/api/v1/attempts/{attempts[PROJECT]}").json()
    assert served == document("status", PROJECT)


def test_a_projects_tree_lists_the_files_status_lists(browser, attempts, document):
    tree = browser.get(f"/api/v1/attempts/{attempts[PROJECT]}/files").json()
    entries = document("status", PROJECT)["files"]["entries"]
    assert [entry["path"] for entry in tree["entries"]] == [entry["path"] for entry in entries]


def test_a_file_reads_as_it_is_on_disk(workspace, browser, attempts):
    response = browser.get(f"/api/v1/attempts/{attempts[PROJECT]}/files/bank/bank.py")
    on_disk = (workspace / "projects" / PROJECT / "bank" / "bank.py").read_text()
    assert response.json()["text"] == on_disk


def test_the_doctor_view_is_cstudy_doctor_json(browser, document):
    assert browser.get("/api/v1/doctor").json() == document("doctor")
