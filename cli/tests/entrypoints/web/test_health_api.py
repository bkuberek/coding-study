"""`GET /api/v1/doctor`: the document of a child `cstudy doctor --json`
(docs/specs/web-ui.md#mock-progress-and-health, docs/specs/web-ui.md#process).

A scripted child stands in for `python -m coding_study`; the slow serve test runs the real one.
"""

import sys
from pathlib import Path

import pytest

from coding_study.entrypoints.web import api_health
from coding_study.entrypoints.web.children import ChildCommand
from tests.web_server import session_client, web_app

ECHO = """
import json, os, sys
print(json.dumps({
    "arguments": sys.argv[1:],
    "cwd": os.getcwd(),
    "no_color": os.environ.get("NO_COLOR"),
    "columns": os.environ.get("COLUMNS"),
}))
sys.exit(EXIT_CODE)
"""
REFUSES = """
import sys
print("error: no workspace here; create one with cstudy init", file=sys.stderr)
sys.exit(EXIT_CODE)
"""
HANGS = "import time\ntime.sleep(30)\n"


def scripted(tmp_path: Path, script: str, exit_code: int = 0) -> ChildCommand:
    path = tmp_path / "child.py"
    path.write_text(script.replace("EXIT_CODE", str(exit_code)))
    return ChildCommand(interpreter=(sys.executable, str(path)))


def doctor(tmp_path: Path, child: ChildCommand):
    with session_client(web_app(tmp_path, child=child)) as client:
        return client.get("/api/v1/doctor")


def error(response) -> tuple[int, str, str]:
    found = response.json()["error"]
    return response.status_code, found["code"], found["message"]


def test_the_doctor_view_is_the_childs_document(tmp_path):
    response = doctor(tmp_path, scripted(tmp_path, ECHO))
    assert (response.status_code, response.json()["arguments"]) == (
        200,
        ["--workspace", str(tmp_path), "doctor", "--json"],
    )


def test_a_failing_check_still_answers_the_document(tmp_path):
    response = doctor(tmp_path, scripted(tmp_path, ECHO, exit_code=4))
    assert response.status_code == 200


def test_the_child_names_the_content_the_server_was_started_with(tmp_path):
    child = scripted(tmp_path, ECHO)
    content = tmp_path / "content"
    response = doctor(tmp_path, ChildCommand(content, child.interpreter))
    assert response.json()["arguments"] == [
        "--workspace",
        str(tmp_path),
        "--content",
        str(content),
        "doctor",
        "--json",
    ]


def test_the_child_runs_in_the_workspace_without_colour_at_120_columns(tmp_path):
    document = doctor(tmp_path, scripted(tmp_path, ECHO)).json()
    assert (Path(document["cwd"]).resolve(), document["no_color"], document["columns"]) == (
        tmp_path.resolve(),
        "1",
        "120",
    )


def test_a_child_that_refuses_answers_its_exit_codes_error_with_its_message(tmp_path):
    response = doctor(tmp_path, scripted(tmp_path, REFUSES, exit_code=3))
    assert error(response) == (422, "usage", "no workspace here; create one with cstudy init")


def test_a_child_that_fails_without_a_document_is_an_internal_error(tmp_path):
    response = doctor(tmp_path, scripted(tmp_path, REFUSES, exit_code=70))
    assert error(response)[:2] == (500, "internal")


def test_an_environment_error_without_a_document_is_503(tmp_path):
    response = doctor(tmp_path, scripted(tmp_path, REFUSES, exit_code=4))
    assert error(response)[:2] == (503, "environment")


def test_a_child_past_its_deadline_gets_503_environment(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api_health, "DOCTOR_DEADLINE_S", 0.5)
    response = doctor(tmp_path, scripted(tmp_path, HANGS))
    assert error(response) == (
        503,
        "environment",
        "cstudy doctor --json did not finish within 0.5 s",
    )
