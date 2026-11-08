"""The states of the Docker engine and what each asks of you
(docs/specs/service-projects.md#docker-states).

The wording lives here, in one place, so `cstudy start`, `cstudy show` and `cstudy doctor` match.
This runs on your own Docker, which you use for other work: `cstudy` starts the engine when a
service project needs it, and never stops it, changes a setting of it or asks you to.
"""

from dataclasses import dataclass
from enum import StrEnum

MACOS_PLATFORM = "darwin"
INSTALL_REACHES = (
    "A project's install step has the network, so it can reach your LAN and this machine's "
    "loopback services; install scripts stay off, and your app and its tests have no network "
    "at all."
)
"""Said wherever Docker's install or a project's install is mentioned."""
_MACOS_INSTALL = (
    "Docker is not installed. Install Docker Desktop: "
    "https://docs.docker.com/desktop/setup/install/mac-install/ "
    "(its license requires a paid plan at larger companies: "
    "https://docs.docker.com/subscription-billing/desktop-license/). "
    "cstudy does not install Docker itself."
)
_LINUX_INSTALL = (
    "Docker is not installed, or has no compose v2. Install Docker Engine: "
    "https://docs.docker.com/engine/install/ or Docker Desktop: "
    "https://docs.docker.com/get-started/get-docker/ "
    "(Docker Desktop's license requires a paid plan at larger companies: "
    "https://docs.docker.com/subscription-billing/desktop-license/). "
    "cstudy does not install Docker itself, and being in the docker group is effectively root."
)
_GROUP_IS_ROOT = (
    "Being in the docker group is effectively root; cstudy cannot reduce that, and never mounts "
    "the socket into a container."
)
_NOT_A_MEMBER = (
    "Docker refuses this user. Join the docker group: sudo usermod -aG docker $USER, then log in "
    f"again. {_GROUP_IS_ROOT}"
)
_NOT_YET_IN_SESSION = (
    "Docker refuses this session: you are in the docker group, but this session does not have it "
    "yet. Log out and back in, or run newgrp docker in this terminal, then run the command again. "
    f"{_GROUP_IS_ROOT}"
)
_IN_SESSION = (
    "Docker refuses this user, though this session is in the docker group: the socket's own "
    "permissions refuse it. docker context ls names the socket, and ls -l on it shows who may use "
    f"it. {_GROUP_IS_ROOT}"
)
DID_NOT_START = "Docker did not start. Start it yourself, then run the command again."
ROOTLESS_ENGINE_START = "systemctl --user start docker"
"""Rootless Docker's user service, which `cstudy` starts itself: it needs no root."""
_ROOTLESS_STOPPED = (
    f"Docker did not start. It runs as your own user and needs no root: run "
    f"{ROOTLESS_ENGINE_START}, then run the command again."
)
_SOCKET_STOPPED = (
    "Docker did not start. Its socket is listening, so connecting starts the engine, and the "
    "engine did not come up: systemctl status docker says why. Once that is fixed, run the "
    "command again, which starts it."
)
SYSTEM_ENGINE_START = "sudo systemctl start docker"
SYSTEM_ENGINE_STOPPED = (
    f"Docker is not running. It is a system service, and starting a system service needs root; "
    f"cstudy never runs sudo. Run {SYSTEM_ENGINE_START}, then run the command again."
)


class DockerGroup(StrEnum):
    """Where you stand with the docker group, asked only when the engine refuses you."""

    NOT_A_MEMBER = "not a member"
    NOT_YET_IN_SESSION = "a member, not yet in this session"
    """The group database lists you, and this process does not have the group."""
    IN_SESSION = "a member, in this session"


class EngineSetup(StrEnum):
    """What can start a stopped engine on Linux, which decides what `cstudy` tries and says."""

    OTHER = "other"
    """Docker Desktop, or an engine at an address `cstudy` does not know."""
    ROOTLESS = "rootless"
    """Rootless Docker, a service of your own user."""
    SOCKET_ACTIVATED = "system, socket-activated"
    """The system engine, whose `docker.socket` listens and starts it on a connection."""
    SYSTEM = "system"
    """The system engine, with no socket listening for it: only root starts it."""


class EngineStatus(StrEnum):
    NOT_INSTALLED = "not installed"
    NO_PERMISSION = "no permission"
    STOPPED = "not running"
    NO_COMPOSE = "no compose v2"
    RUNNING = "running"


@dataclass(frozen=True, slots=True)
class EngineState:
    status: EngineStatus
    engine_version: str | None = None
    compose_version: str | None = None
    docker_group: DockerGroup | None = None
    """Set only when the engine refuses you."""

    @property
    def running(self) -> bool:
        return self.status is EngineStatus.RUNNING


def install_message(platform: str) -> str:
    instructions = _MACOS_INSTALL if platform == MACOS_PLATFORM else _LINUX_INSTALL
    return f"{instructions} {INSTALL_REACHES}"


def no_permission_message(group: DockerGroup | None) -> str:
    """Only someone outside the group, or of unknown standing, is told to join it."""
    match group:
        case DockerGroup.NOT_YET_IN_SESSION:
            return _NOT_YET_IN_SESSION
        case DockerGroup.IN_SESSION:
            return _IN_SESSION
        case DockerGroup.NOT_A_MEMBER | None:
            return _NOT_A_MEMBER


def did_not_start_message(setup: EngineSetup) -> str:
    """What to do once `cstudy` could not start the engine; `sudo` only where root is needed."""
    match setup:
        case EngineSetup.OTHER:
            return DID_NOT_START
        case EngineSetup.ROOTLESS:
            return _ROOTLESS_STOPPED
        case EngineSetup.SOCKET_ACTIVATED:
            return _SOCKET_STOPPED
        case EngineSetup.SYSTEM:
            return SYSTEM_ENGINE_STOPPED


def engine_problem(state: EngineState, platform: str) -> str | None:
    """Why a service project cannot run on this engine; None when it can."""
    match state.status:
        case EngineStatus.RUNNING:
            return None
        case EngineStatus.STOPPED:
            return DID_NOT_START
        case EngineStatus.NO_PERMISSION:
            return no_permission_message(state.docker_group)
        case EngineStatus.NOT_INSTALLED | EngineStatus.NO_COMPOSE:
            return install_message(platform)
