"""A service project: a `kind: project` problem with `project.grading: http`, which you build as a
small running service and `cstudy` runs in a Docker sandbox
(docs/specs/service-projects.md#manifest-sketch).

Names are fixed and contents are free: `cstudy` calls only the standard command names, and the
language's decisions, the image and the install command, live in the problem's template.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from coding_study.domain.docker_engine import EngineState, EngineStatus, engine_problem
from coding_study.domain.problem import ProblemMeta
from coding_study.domain.sandbox import DEFAULT_READY_S, STARTUP_UP_S, StartupBudget

INSTALL_LIMIT_S = 600
HELPER_IMAGE_MB = 41
"""The pinned Python image of the forwarder, in every stack; a mock server shares it."""
_APP_ROW = "app"
_MOCK_ROW = "mocks"
TEST_LIMIT_S = 120
RESET_LIMIT_S = 30
PROBLEM_PLACEHOLDER = "{problem}"
"""The one placeholder an argument list may use, and only in `grade_setup`."""
LOCK_MANAGERS: Mapping[str, str] = {"pnpm-lock.yaml": "pnpm", "uv.lock": "uv"}
"""The package manager a lock file names, for the list of what a problem depends on."""
INSTALLED_DIRECTORIES: Mapping[str, str] = {"pnpm-lock.yaml": "node_modules", "uv.lock": ".venv"}
"""Where the install of a lock file leaves its packages: gone with `--fresh`, so installed again."""
FROZEN_INSTALL_FLAGS: Mapping[str, tuple[str, ...]] = {
    "pnpm": ("--frozen-lockfile", "--ignore-scripts"),
    "uv": ("--frozen", "--no-build"),
}
"""What `commands.install` must say to a known package manager: the lock exactly, and no code of a
package's at install. Another tool's install is judged by what it does: the lock's digest must stay
the same."""


@dataclass(frozen=True, slots=True)
class ServiceCommands:
    """The lifecycle commands, each an argument list run with no shell."""

    run: tuple[str, ...]
    test: tuple[str, ...]
    install: tuple[str, ...] | None = None
    bootstrap: tuple[str, ...] | None = None
    reset: tuple[str, ...] | None = None
    grade_setup: tuple[str, ...] | None = None

    def declared(self) -> Mapping[str, tuple[str, ...]]:
        commands = {
            "install": self.install,
            "bootstrap": self.bootstrap,
            "run": self.run,
            "test": self.test,
            "reset": self.reset,
            "grade_setup": self.grade_setup,
        }
        return {name: command for name, command in commands.items() if command is not None}


@dataclass(frozen=True, slots=True)
class ServiceApp:
    port_env: str
    port: int
    health: str
    ready_timeout_s: int = DEFAULT_READY_S
    mem_limit: str | None = None


@dataclass(frozen=True, slots=True)
class ServiceMock:
    name: str
    config: str
    """Relative to the problem's directory, never the starter."""


@dataclass(frozen=True, slots=True)
class ServiceSizes:
    install_mb: int | None = None
    images_mb: Mapping[str, int] = field(default_factory=dict[str, int])
    """The download of each image, by `app`, `mocks` or a service's name."""
    memory_mb: int | None = None


@dataclass(frozen=True, slots=True)
class ServiceRequires:
    lock: str | None = None
    services: tuple[str, ...] = ()
    sizes: ServiceSizes = field(default_factory=ServiceSizes)


@dataclass(frozen=True, slots=True)
class ServiceTimeouts:
    """`startup` is the first clock's, and the others the limits of one command each."""

    startup: int = STARTUP_UP_S
    install: int = INSTALL_LIMIT_S
    test: int = TEST_LIMIT_S
    reset: int = RESET_LIMIT_S


@dataclass(frozen=True, slots=True)
class ServiceProject:
    image: str
    """The toolchain image, pinned by digest."""
    commands: ServiceCommands
    app: ServiceApp
    env: Mapping[str, str]
    """The whole environment of the app; the starter's `.env` repeats it."""
    requires: ServiceRequires
    mocks: tuple[ServiceMock, ...] = ()
    services: str | None = None
    """The problem's compose file of backing services, relative to its directory."""
    install_env: Mapping[str, str] = field(default_factory=dict[str, str])
    """What the package manager needs in its install container: where its cache is."""
    timeouts: ServiceTimeouts = field(default_factory=ServiceTimeouts)

    @property
    def startup_budget(self) -> StartupBudget:
        return StartupBudget(self.timeouts.startup, self.app.ready_timeout_s)


def service_of(meta: ProblemMeta) -> ServiceProject | None:
    """The problem's service block; None for any other problem, which never needs Docker."""
    return meta.project.service if meta.project is not None else None


@dataclass(frozen=True, slots=True)
class NeedRow:
    """One line of what a problem depends on (docs/specs/service-projects.md#where-it-shows)."""

    label: str
    text: str
    problem: str | None = None
    """Why it is not met on this machine; None when it is."""


def service_needs(
    meta: ProblemMeta, service: ServiceProject, state: EngineState, platform: str
) -> tuple[NeedRow, ...]:
    """What the problem depends on and whether this machine has it. The figures are the problem's
    own declaration, shown before anything downloads."""
    sizes = service.requires.sizes
    rows = [_docker_need(state, platform), _language_need(meta, service)]
    lock = service.requires.lock
    if lock is not None:
        manager = LOCK_MANAGERS.get(lock, lock)
        rows.append(NeedRow("packages", f"{manager} · about {sizes.install_mb} MB installed"))
    for name in service.requires.services:
        rows.append(NeedRow("services", f"{name} · {sizes.images_mb.get(name)} MB download"))
    if service.mocks:
        names = ", ".join(mock.name for mock in service.mocks)
        rows.append(NeedRow("mocks", f"{names} · {sizes.images_mb.get(_MOCK_ROW)} MB download"))
    rows.append(_total_need(service))
    return tuple(rows)


def _docker_need(state: EngineState, platform: str) -> NeedRow:
    what = "running engine and compose v2"
    if state.status is EngineStatus.STOPPED:
        return NeedRow("docker", f"{what}: not running, and started when it is needed")
    return NeedRow("docker", what, engine_problem(state, platform))


def _language_need(meta: ProblemMeta, service: ServiceProject) -> NeedRow:
    language = meta.languages[0] if meta.languages else "?"
    image = service.image.partition("@")[0]
    size = service.requires.sizes.images_mb.get(_APP_ROW)
    return NeedRow("language", f"{language} · {image}, {size} MB download")


def _total_need(service: ServiceProject) -> NeedRow:
    sizes = service.requires.sizes
    helper = 0 if _MOCK_ROW in sizes.images_mb else HELPER_IMAGE_MB
    download = sum(sizes.images_mb.values()) + helper + (sizes.install_mb or 0)
    return NeedRow("total", f"about {download} MB download, about {sizes.memory_mb} MB memory")


def parse_env_file(text: str) -> dict[str, str]:
    """The variables of a `.env`: `NAME=value` lines, without blank lines and `#` comments. No
    quoting: it holds fixed values, and cstudy does not read it to start anything."""
    variables: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            name, _, value = stripped.partition("=")
            variables[name.strip()] = value.strip()
    return variables
