"""The API's own documents against `schemas/web-api.schema.json`
(docs/specs/web-ui.md#api-conventions): the real responses of servers over test workspaces, each
validated against the definition of its endpoint, refusals against `error`. The documents a command
also prints (`cstudy list --json`, `status --json`, `history --json`, `next --json`,
`stats --json`, `doctor --json`, the export) are compared with that command's output by the tests
of their endpoints instead."""

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncGenerator, Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from starlette.testclient import TestClient

from coding_study.application.attempt_changes import WatchedFolder, workspace_snapshot
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.notifications import Notifications, WorkspaceWatch
from coding_study.entrypoints.web.runs import Children
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, SCHEMAS_DIRECTORY, copy_catalog_problems
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.scripted_runs import PASSING_RUN, QUICK, WAIT_S, Script, eventually, frames, outs
from tests.web_server import WRITE_HEADERS, anonymous_client, session_client, web_app

SCHEMA = json.loads((SCHEMAS_DIRECTORY / "web-api.schema.json").read_text())
DOCUMENTS = (
    "session",
    "preferences",
    "config",
    "code_intelligence_languages",
    "error",
    "problem",
    "statement",
    "hint",
    "done",
    "solution",
    "file_tree",
    "file",
    "past_files",
    "past_file",
    "file_saved",
    "file_restored",
    "child_started",
    "job",
    "run",
    "runs",
    "closed",
    "job_line",
    "mock_state",
    "mock_started",
    "imported",
    "file_changed",
    "attempt_changed",
    "progress_changed",
    "run_notice",
    "job_notice",
)
NOTICES = {
    "file_changed": "file_changed",
    "attempt_changed": "attempt_changed",
    "progress_changed": "progress_changed",
    "run_started": "run_notice",
    "run_ended": "run_notice",
    "job_started": "job_notice",
    "job_ended": "job_notice",
}
"""The definition of each notification's data."""
MOCK_CATALOG = (*FIRST_CATALOG, "0007-group-anagrams", "0014-first-missing-positive")
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
FILE = "bank/bank.py"
PREFERENCES = "/api/v1/preferences"
CONFIG = "/api/v1/config"
LANGUAGES = "/api/v1/code-intelligence/languages"
REFUSED = 400

type Documents = dict[str, list[Any]]


class Recorder:
    """The documents of the responses it is given, by definition; a refusal is an `error`."""

    def __init__(self) -> None:
        self.documents: Documents = defaultdict(list)

    def __call__(self, definition: str, response: Any) -> Any:
        name = "error" if response.status_code >= REFUSED else definition
        self.documents[name].append(response.json())
        return response

    def stream(self, body: str) -> None:
        """The data of a run's or a job's events that the API defines: `closed` and `line`."""
        for frame in frames(body):
            if frame.event == "closed":
                self.documents["closed"].append(frame.data)
            elif frame.event == "line":
                self.documents["job_line"].append(frame.data)

    def notices(self, sent: Sequence[str]) -> None:
        for frame in frames("".join(sent)):
            self.documents[NOTICES[frame.event]].append(frame.data)


@pytest.fixture(scope="module")
def documents(tmp_path_factory: pytest.TempPathFactory) -> Documents:
    record = Recorder()
    export = _practice(tmp_path_factory.mktemp("practice"), record)
    _import(tmp_path_factory.mktemp("import"), export, record)
    _mock(tmp_path_factory.mktemp("mock"), record)
    _watch(tmp_path_factory.mktemp("watch"), record)
    return record.documents


def _practice(root: Path, record: Recorder) -> dict[str, Any]:
    """A project attempt from start to done, through every endpoint of its files, runs, jobs and
    the refusals on the way; the export of its progress."""
    environment = project_environment(root, ScriptedProjectProcess())
    attempt = start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt.id
    script = Script(root / "script.json")
    notifications = Notifications()
    app = web_app(root, environment, script.child, Children(QUICK), notifications)
    with session_client(app) as client:
        record("session", client.get("/api/v1/session"))
        record("preferences", client.get(PREFERENCES))
        record("preferences", client.put(PREFERENCES, json={"vim": True}, headers=WRITE_HEADERS))
        record("config", client.get(CONFIG))
        change = {"changes": {"bench.reps": 3}}
        record("config", client.post(CONFIG, json=change, headers=WRITE_HEADERS))
        record("code_intelligence_languages", client.get(LANGUAGES))
        record("error", client.delete("/api/v1/session", headers=WRITE_HEADERS))
        record("error", client.post(PREFERENCES, json={}, headers={"Origin": "http://evil"}))
        record("problem", client.get(f"/api/v1/problems/{PROJECT_SLUG}"))
        record("statement", client.get(f"/api/v1/problems/{PROJECT_SLUG}/statement"))
        record("error", client.get("/api/v1/problems/no-such-problem"))
        _files(client, record, attempt)
        record("hint", client.post(f"/api/v1/attempts/{attempt}/hints", headers=WRITE_HEADERS))
        _run(client, record, script, attempt)
        _job(client, record, script)
        record("mock_state", client.get("/api/v1/mock"))
        record("mock_started", client.post("/api/v1/mock", json={}, headers=WRITE_HEADERS))
        solution = f"/api/v1/problems/{PROJECT_SLUG}/solution"
        record("error", client.post(solution, json={}, headers=WRITE_HEADERS))
        record("solution", client.post(solution, json={"confirm": True}, headers=WRITE_HEADERS))
        done = {"gave_up": True}
        record(
            "done",
            client.post(f"/api/v1/attempts/{attempt}/done", json=done, headers=WRITE_HEADERS),
        )
        record("error", client.get(f"/api/v1/attempts/{attempt}"))
        _past_files(client, record, attempt)
        export = client.get("/api/v1/progress/export").json()
        assert client.portal is not None, "the client runs the app in a loop of its own"
        record.notices(client.portal.call(_everything_sent, notifications))
    return export


def _files(client: TestClient, record: Recorder, attempt: int) -> None:
    files = f"/api/v1/attempts/{attempt}/files"
    record("file_tree", client.get(files))
    etag = record("file", client.get(f"{files}/{FILE}")).headers["etag"]
    saved = {**WRITE_HEADERS, "If-Match": etag}
    record("file_saved", client.put(f"{files}/{FILE}", json={"text": "pass\n"}, headers=saved))
    record("error", client.put(f"{files}/{FILE}", json={"text": "again\n"}, headers=saved))
    record("error", client.put(f"{files}/{FILE}", json={"text": "again\n"}, headers=WRITE_HEADERS))
    new = {**WRITE_HEADERS, "If-None-Match": "*"}
    created = record(
        "file_saved", client.put(f"{files}/bank/notes.py", json={"text": "x\n"}, headers=new)
    )
    moving = {**WRITE_HEADERS, "If-Match": created.headers["etag"]}
    to_kept = {"to": "bank/kept.py"}
    record("file_saved", client.post(f"{files}/bank/notes.py/move", json=to_kept, headers=moving))
    record("error", client.post(f"{files}/bank/kept.py/move", json=to_kept, headers=moving))
    restore = f"/api/v1/attempts/{attempt}/restore"
    record("file_restored", client.post(restore, json={"path": FILE}, headers=WRITE_HEADERS))


def _past_files(client: TestClient, record: Recorder, attempt: int) -> None:
    """The finished attempt's files, which are the project folder as it is now."""
    past = f"/api/v1/attempts/{attempt}/past-files"
    record("past_files", client.get(past))
    record("past_file", client.get(f"{past}/{FILE}"))
    record("error", client.get(f"{past}/no/such/file.py"))


def _run(client: TestClient, record: Recorder, script: Script, attempt: int) -> None:
    script.play(*outs(*PASSING_RUN), {"exit": 0})
    body = {"attempt_id": attempt, "command": "test"}
    run = record("child_started", client.post("/api/v1/runs", json=body, headers=WRITE_HEADERS))
    path = f"/api/v1/runs/{run.json()['id']}"
    eventually(lambda: client.get(path).json()["state"], "ended".__eq__)
    record("run", client.get(path))
    record("runs", client.get(f"/api/v1/runs?attempt_id={attempt}"))
    record.stream(client.get(f"{path}/events").text)
    record("error", client.post(f"{path}/cancel", headers=WRITE_HEADERS))


def _job(client: TestClient, record: Recorder, script: Script) -> None:
    script.play({"out": "ok    workspace"}, {"err": "warning: slow"}, {"exit": 0})
    record(
        "error", client.post("/api/v1/jobs", json={"command": "doctor_fix"}, headers=WRITE_HEADERS)
    )
    body = {"command": "doctor_fix", "confirm": True}
    job = record("child_started", client.post("/api/v1/jobs", json=body, headers=WRITE_HEADERS))
    path = f"/api/v1/jobs/{job.json()['id']}"
    eventually(lambda: client.get(path).json()["state"], "ended".__eq__)
    record("job", client.get(path))
    record.stream(client.get(f"{path}/events").text)


async def _everything_sent(notifications: Notifications) -> list[str]:
    notifications.stop()
    return [frame async for frame in notifications.frames(-1)]


def _import(root: Path, export: dict[str, Any], record: Recorder) -> None:
    """The export of the practice imported into a workspace with no progress yet."""
    body = {"confirm": True, "export": export}
    app = web_app(root)
    with anonymous_client(app) as anonymous:
        record("error", anonymous.get("/api/v1/session"))
    with session_client(app) as client:
        record("imported", client.post("/api/v1/progress/import", json=body, headers=WRITE_HEADERS))


def _mock(root: Path, record: Recorder) -> None:
    problems = copy_catalog_problems(root / "catalog", MOCK_CATALOG)
    workspace = repository_root(root / "workspace", problems, FIXTURE_TRACKS)
    environment = make_environment(workspace, toolchains=FakeToolchains(stub_generators=STUBS))
    with session_client(web_app(workspace, environment)) as client:
        record("mock_started", client.post("/api/v1/mock", json={}, headers=WRITE_HEADERS))
        record("mock_state", client.get("/api/v1/mock"))


class OneBurst:
    """A watch of the workspace that sees one burst of changes, which `change` makes as the watch
    starts; `handled` is set once the server read it."""

    def __init__(self, change: Callable[[], None]) -> None:
        self._change = change
        self.handled = asyncio.Event()

    async def folder_changes(
        self, root: Path, folders: Sequence[WatchedFolder], stop_event: asyncio.Event
    ) -> AsyncGenerator[None]:
        self._change()
        yield None
        self.handled.set()
        await stop_event.wait()


def _watch(root: Path, record: Recorder) -> None:
    """The notices of a file saved on disk, a statement rewritten and the attempt's row changed."""
    environment = project_environment(root, ScriptedProjectProcess())
    attempt = start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt

    def change() -> None:
        environment.workspace.absolute(f"projects/{PROJECT_SLUG}/{FILE}").write_text("x = 1\n")
        statement = environment.workspace.absolute(f".statements/{PROJECT_SLUG}.md")
        statement.write_text(f"{statement.read_text()}\nmore\n")
        environment.progress.update_attempt(replace(attempt, solution_revealed=True))

    record.notices(asyncio.run(_watched(environment, OneBurst(change))))


async def _watched(environment: Environment, burst: OneBurst) -> list[str]:
    async def snapshot(previous: Any) -> Any:
        return workspace_snapshot(environment, previous)

    notifications = Notifications()
    watch = asyncio.create_task(WorkspaceWatch(notifications, burst, snapshot).run())
    await asyncio.wait_for(burst.handled.wait(), WAIT_S)
    sent = await _everything_sent(notifications)
    await asyncio.wait_for(watch, WAIT_S)
    return sent


def test_the_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("definition", DOCUMENTS)
def test_the_api_answers_documents_of_the_definition(documents, definition):
    assert documents[definition], f"no {definition} document seen"


@pytest.mark.parametrize("definition", DOCUMENTS)
def test_every_document_matches_its_definition(documents, definition):
    validator = Draft202012Validator({"$ref": f"#/$defs/{definition}", "$defs": SCHEMA["$defs"]})
    problems = [
        f"{error.json_path}: {error.message}"
        for document in documents[definition]
        for error in validator.iter_errors(document)
    ]
    assert problems == []
