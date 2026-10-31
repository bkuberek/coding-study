"""What the request handlers share: the server's settings and its worker."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from starlette.requests import Request

from coding_study.application.environment import Environment
from coding_study.application.ports import PreferencesStore
from coding_study.entrypoints.web.children import ChildCommand
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
    child: ChildCommand = field(default_factory=ChildCommand)
    """How the server starts a child `cstudy`."""
    lock_deadline_s: float = LOCK_DEADLINE_S


@dataclass(frozen=True, slots=True)
class ServerState:
    settings: ServerSettings
    worker: UseCaseWorker = field(default_factory=UseCaseWorker)


def server_state(request: Request) -> ServerState:
    return cast(ServerState, request.app.state.server)


async def in_workspace[*Arguments, Result](
    request: Request, use: Callable[[Environment, *Arguments], Result], *arguments: *Arguments
) -> Result:
    """`use` called on the worker with a fresh Environment of the server's workspace, as a
    command builds one for its run."""
    server = server_state(request)
    load_environment = server.settings.load_environment
    return await server.worker.run(lambda: use(load_environment(), *arguments))
