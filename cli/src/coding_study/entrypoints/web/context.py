"""What the request handlers share: the server's settings and its worker."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from starlette.requests import HTTPConnection

from coding_study.adapters.watchfiles_watcher import WatchfilesWatcher
from coding_study.application.environment import Environment
from coding_study.application.ports import ConfigFile, PreferencesStore
from coding_study.entrypoints.web.children import ChildCommand
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from coding_study.entrypoints.web.notifications import FolderWatcher, Notifications
from coding_study.entrypoints.web.runs import Children
from coding_study.entrypoints.web.security import SessionSecrets
from coding_study.entrypoints.web.worker import UseCaseWorker

LOCK_DEADLINE_S = 5.0
"""How long a file change waits for its project's lock (docs/specs/web-ui.md#file-scope)."""


@dataclass(frozen=True, slots=True)
class ServerSettings:
    port: int
    version: str
    """The running `cstudy` version."""
    secrets: SessionSecrets
    static_directory: Path
    """The built front end and its `manifest.json`."""
    load_environment: Callable[[], Environment]
    """A fresh Environment of the server's workspace, for each use case call."""
    preferences: PreferencesStore
    config_file: ConfigFile
    """The user's `config.toml`, which Settings edits."""
    child: ChildCommand = field(default_factory=ChildCommand)
    """How the server starts a child `cstudy`."""
    lock_deadline_s: float = LOCK_DEADLINE_S
    watcher: FolderWatcher = field(default_factory=WatchfilesWatcher)
    """Watches the folders the notifications cover."""


@dataclass(frozen=True, slots=True)
class ServerState:
    settings: ServerSettings
    worker: UseCaseWorker = field(default_factory=UseCaseWorker)
    children: Children = field(default_factory=Children)
    """The runs and jobs."""
    notifications: Notifications = field(default_factory=Notifications)
    """The notification streams of the tabs."""
    sessions: LanguageSessions = field(default_factory=LanguageSessions)
    """The code-intelligence sessions, each a WebSocket and a language server."""


def server_state(request: HTTPConnection) -> ServerState:
    """The server's state, for a request or a WebSocket."""
    return cast(ServerState, request.app.state.server)


async def in_workspace[*Arguments, Result](
    request: HTTPConnection,
    use: Callable[[Environment, *Arguments], Result],
    *arguments: *Arguments,
) -> Result:
    """`use` called on the worker with a fresh Environment of the server's workspace, as a
    command builds one for its run."""
    server = server_state(request)
    load_environment = server.settings.load_environment
    return await server.worker.run(lambda: use(load_environment(), *arguments))
