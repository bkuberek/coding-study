"""What the request handlers share: the server's settings and its worker."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from starlette.requests import Request

from coding_study.application.environment import Environment
from coding_study.application.ports import PreferencesStore
from coding_study.entrypoints.web.security import SessionSecrets
from coding_study.entrypoints.web.worker import UseCaseWorker


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


@dataclass(frozen=True, slots=True)
class ServerState:
    settings: ServerSettings
    worker: UseCaseWorker = field(default_factory=UseCaseWorker)


def server_state(request: Request) -> ServerState:
    return cast(ServerState, request.app.state.server)
