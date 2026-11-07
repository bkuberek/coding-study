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
_NO_PERMISSION = (
    "Docker refuses this user. Join the docker group: sudo usermod -aG docker $USER, then log in "
    "again. Being in the docker group is effectively root; cstudy cannot reduce that, and never "
    "mounts the socket into a container."
)
DID_NOT_START = "Docker did not start. Start it yourself, then run the command again."
SYSTEM_ENGINE_START = "sudo systemctl start docker"
SYSTEM_ENGINE_STOPPED = (
    f"Docker is not running, and starting a system engine needs root. cstudy never runs sudo: "
    f"run {SYSTEM_ENGINE_START}, then run the command again."
)


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

    @property
    def running(self) -> bool:
        return self.status is EngineStatus.RUNNING


def install_message(platform: str) -> str:
    instructions = _MACOS_INSTALL if platform == MACOS_PLATFORM else _LINUX_INSTALL
    return f"{instructions} {INSTALL_REACHES}"


def no_permission_message() -> str:
    return _NO_PERMISSION


def engine_problem(state: EngineState, platform: str) -> str | None:
    """Why a service project cannot run on this engine; None when it can."""
    match state.status:
        case EngineStatus.RUNNING:
            return None
        case EngineStatus.STOPPED:
            return DID_NOT_START
        case EngineStatus.NO_PERMISSION:
            return no_permission_message()
        case EngineStatus.NOT_INSTALLED | EngineStatus.NO_COMPOSE:
            return install_message(platform)
