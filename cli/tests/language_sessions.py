"""The code-intelligence WebSocket under Starlette's test client (docs/specs/web-ui.md#testing): a
workspace with a Python attempt in progress and its server installed, a scripted server behind it,
and the handshakes of the page and of the pages that attack it."""

import json
from collections.abc import Callable, Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient, WebSocketDenialResponse, WebSocketTestSession
from starlette.types import ASGIApp
from starlette.websockets import WebSocketDisconnect

from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.application.attempt_changes import WorkspaceChange
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import Attempt
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.code_intelligence import MAX_SESSIONS, LanguageSessions
from coding_study.entrypoints.web.language_server import LanguageTiming
from coding_study.entrypoints.web.notifications import Notifications
from tests.fakes import (
    INSTALLED_SERVERS,
    FakeLanguageServers,
    FakeStubGenerator,
    FakeToolchains,
    jdk_of,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_TRACKS
from tests.language_server_scripts import QUICK, ScriptedServer
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.web_server import HOST, ORIGIN, SECRETS, web_app

PRACTICE = Path(__file__).resolve().parent / "fixtures" / "practice" / "problems"
PATH = "/api/v1/code-intelligence"
PAGE_HEADERS: Mapping[str, str] = {"Origin": ORIGIN}
"""What the page's own handshake carries besides the cookie the test client holds."""
CSRF_MESSAGE = {"csrf": SECRETS.csrf}
WAIT_S = 10.0
CODE_INTELLIGENCE_ON = Preferences(code_intelligence=True)
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
_POOL = ThreadPoolExecutor(max_workers=4)


@dataclass
class Rig:
    """An app whose attempt 1 is a Python practice file and whose servers are `server`."""

    root: Path
    environment: Environment
    sessions: LanguageSessions
    server: ScriptedServer
    attempt: Attempt
    notifications: Notifications = field(default_factory=Notifications)
    """The hub whose file changes the sessions pass to their servers."""

    @property
    def app(self) -> ASGIApp:
        return web_app(
            self.root, self.environment, notifications=self.notifications, sessions=self.sessions
        )

    @property
    def python_root(self) -> str:
        """The root of the Python session as a `file:` URI."""
        return (self.root / "python").as_uri()

    @property
    def document(self) -> str:
        """A file inside that root."""
        return f"{self.python_root}/practice/two_sum.py"

    @property
    def query(self) -> str:
        return f"?attempt_id={self.attempt.id}"

    def start(self, language: Language) -> Attempt:
        return start_attempt(self.environment, StartRequest("two-sum", language)).attempt

    def turn_off(self) -> None:
        FsPreferencesStore(self.root).write(preferences_document(Preferences()))


def rig(
    tmp_path: Path,
    timing: LanguageTiming = QUICK,
    installed: bool = True,
    limit: int = MAX_SESSIONS,
    project: bool = False,
    language: Language = Language.PYTHON,
    licenses_accepted: bool = True,
) -> Rig:
    """`project`: attempt 1 is the fixture project, rooted in its folder; otherwise the practice
    file of `language`, on JDK 25. Without `licenses_accepted`, the workspace's marker records no
    license, so the Kotlin LSP is not usable."""
    probes = INSTALLED_SERVERS if installed else {}
    servers = FakeLanguageServers(probes)
    if not licenses_accepted:
        servers.accepted.clear()
    if project:
        environment = project_environment(
            tmp_path, ScriptedProjectProcess(), language_servers=servers
        )
        attempt = start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt
    else:
        for project_directory in ("python", "jvm", "go", "rust"):
            (tmp_path / project_directory).mkdir(parents=True, exist_ok=True)
        environment = make_environment(
            repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
            toolchains=FakeToolchains(stub_generators=STUBS),
            language_servers=servers,
            content_root=tmp_path / "reference-content",
            jdk=jdk_of(25),
        )
        attempt = start_attempt(environment, StartRequest("two-sum", language)).attempt
    FsPreferencesStore(tmp_path).write(preferences_document(CODE_INTELLIGENCE_ON))
    scripted = ScriptedServer(tmp_path / "server.json")
    sessions = LanguageSessions(scripted.command, timing, limit)
    return Rig(tmp_path, environment, sessions, scripted, attempt)


def address(query: str, host: str = HOST) -> str:
    return f"ws://{host}{PATH}{query}"


def connect(
    client: TestClient,
    query: str,
    headers: Mapping[str, str] = PAGE_HEADERS,
    host: str = HOST,
) -> Any:
    """The handshake of a page: `with connect(…) as websocket`."""
    return client.websocket_connect(address(query, host), headers=dict(headers))


@contextmanager
def session(client: TestClient, query: str) -> Iterator[WebSocketTestSession]:
    """The page's handshake and its CSRF message: the server starts."""
    with connect(client, query) as websocket:
        websocket.send_json(CSRF_MESSAGE)
        yield websocket


def stopped(client: TestClient, sessions: LanguageSessions) -> None:
    """The server stops: `cstudy serve`'s Ctrl-C, as far as the sessions go."""
    portal = client.portal
    assert portal is not None
    portal.call(sessions.stop)


def stopped_within(client: TestClient, sessions: LanguageSessions, seconds: float) -> None:
    """Like `stopped`, but fails instead of waiting for ever for a stop that hangs."""
    portal = client.portal
    assert portal is not None
    portal.start_task_soon(sessions.stop).result(timeout=seconds)


def noticed(client: TestClient, hub: Notifications, change: WorkspaceChange) -> None:
    """The workspace watch tells the hub of a change, on the server's event loop."""
    portal = client.portal
    assert portal is not None

    async def notice() -> None:
        hub.notice(change)

    portal.call(notice)


def refused(client: TestClient, query: str, **handshake: Any) -> WebSocketDenialResponse:
    """The response that refused the handshake."""
    with pytest.raises(WebSocketDenialResponse) as denial, connect(client, query, **handshake):
        pass
    return denial.value


def received_text(websocket: WebSocketTestSession, seconds: float = WAIT_S) -> str:
    """The next message, or WebSocketDisconnect at a close; fails instead of waiting for ever."""
    return _within(websocket.receive_text, seconds)


def received(websocket: WebSocketTestSession, seconds: float = WAIT_S) -> Any:
    return json.loads(received_text(websocket, seconds))


def closed_with(websocket: WebSocketTestSession) -> tuple[int, str]:
    """The code and reason of the close that comes next."""
    with pytest.raises(WebSocketDisconnect) as closed:
        received_text(websocket)
    return closed.value.code, closed.value.reason or ""


def _within[Value](receive: Callable[[], Value], seconds: float) -> Value:
    return _POOL.submit(receive).result(timeout=seconds)
