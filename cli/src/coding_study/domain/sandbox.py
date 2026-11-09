"""The sandbox of a service project: the compose file `cstudy` generates, what a stack is called,
and what counts as a leftover (docs/specs/service-projects.md#sandbox).

The hardening, the networks and the labels live here and nowhere else. The file is rendered with
no interpolation left: an IDE or a sweep may read it without `cstudy`'s environment, and a `$` in a
problem's command or environment stays literal.

Two clocks meet here, and they stay apart (docs/specs/service-projects.md#two-clocks). The startup
budget (`StartupBudget`) covers everything up to the moment a stack is ready, and a failure of it
says so and changes no result. A limit on a test or a case starts at `ReadyStack.ready_at`.
"""

import hashlib
import itertools
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from coding_study.domain.errors import SandboxError

PYTHON_IMAGE = (
    "python:3.13-slim@sha256:09a17cad02668ae61ece136b4fd36ac3849e14f670ebedb637ea3e15580525bc"
)
"""The volume owners, the forwarder and the mock server: nothing is built, and the digest of the
multi-architecture index holds on arm64 and amd64."""

APP_SERVICE = "app"
BOOTSTRAP_SERVICE = "bootstrap"
GRADE_SETUP_SERVICE = "grade_setup"
RESET_PREPARE_SERVICE = "reset-prepare"
EGRESS_PROBE_SERVICE = "cstudy-egress-probe"
DATA_OWNER_SERVICE = "data-owner"
CACHE_OWNER_SERVICE = "cache-owner"
INSTALL_SERVICE = "install"
MOCK_SERVICE = "cstudy-mocks"
FORWARD_SERVICE = "cstudy-forward"
RESERVED_SERVICES = frozenset(
    {
        APP_SERVICE,
        BOOTSTRAP_SERVICE,
        GRADE_SETUP_SERVICE,
        RESET_PREPARE_SERVICE,
        EGRESS_PROBE_SERVICE,
        DATA_OWNER_SERVICE,
        CACHE_OWNER_SERVICE,
        INSTALL_SERVICE,
        MOCK_SERVICE,
        FORWARD_SERVICE,
    }
)
"""Names no mock server or backing service may take."""
DATA_VOLUME = "data"
CACHE_VOLUME = "cache"
RESERVED_VOLUMES = frozenset({DATA_VOLUME, CACHE_VOLUME})
"""The stack's own volumes, which no problem volume may name."""
CONTROL_PORT = 9000
MOCK_PORT = 8080
REACH_FIRST_PORT = 10000
"""Where the forwarder listens for the first service the grader may reach; each next one takes the
next free port."""

LABEL_KIND = "cstudy.kind"
LABEL_WORKSPACE = "cstudy.workspace"
LABEL_SLUG = "cstudy.slug"
LABEL_OWNER = "cstudy.owner_pid"
"""On containers only: a label that changes on a volume makes compose ask whether to recreate it,
and that question hangs on an open pipe and loses data under `-y`."""
LABEL_PROJECT = "com.docker.compose.project"

HOME_DIRECTORY = "/tmp/home"
TEMPORARY_DIRECTORY = "/tmp"
DATA_DIRECTORY = "/data"
CACHE_DIRECTORY = "/cache"
PROBLEM_DIRECTORY = "/cstudy/problem"
"""What `{problem}` in a `grade_setup` command expands to."""
FORWARDER_FILE = "forward.py"
FORWARDER_PATH = f"/cstudy/{FORWARDER_FILE}"
MOCK_CODE_DIRECTORY = "mock_server"
MOCK_CODE_PATH = f"/cstudy/{MOCK_CODE_DIRECTORY}"
MOCK_CONFIG_FILE = "mocks.json"
MOCK_CONFIG_PATH = f"/cstudy/{MOCK_CONFIG_FILE}"
MOCK_COMMAND = ("python", "-I", MOCK_CODE_PATH, MOCK_CONFIG_PATH)
RESET_PHASE_VARIABLE = "CSTUDY_RESET_PHASE"
RESET_PHASE_PREPARE = "prepare"
RESET_PHASE_APPLY = "apply"
PASSWD_FILE = "passwd"
STACK_FILE = "stack.yaml"
SERVICE_FILES_DIRECTORY = "services"
"""Under `.cs/runs/<stack>/`: a copy of each file a backing service's bind mount names, since the
problem's own folder may lie where Docker Desktop shares nothing."""
SANDBOX_NETWORK = "sandbox"
NO_NEW_PRIVILEGES = "no-new-privileges:true"
BACKING_SERVICE_FIELDS = frozenset(
    {
        "image",
        "command",
        "entrypoint",
        "environment",
        "healthcheck",
        "mem_limit",
        "pids_limit",
        "volumes",
        "tmpfs",
        "user",
        "working_dir",
        "read_only",
        "depends_on",
        "stop_grace_period",
        "stop_signal",
        "shm_size",
        "init",
    }
)
"""What a problem's compose file may set on a backing service. Anything else is S21's to refuse and
never reaches a stack: the networks, labels, logs, capabilities and privileges are `cstudy`'s."""
DEVCONTAINER_DIRECTORY = ".devcontainer"
"""A file in the project that a host tool obeys, so sandboxed code may read it and not write it."""

APP_MEMORY = "512m"
APP_PIDS = 256
HELPER_MEMORY = "64m"
HELPER_PIDS = 32
OWNER_MEMORY = "32m"
OWNER_PIDS = 16
INSTALL_MEMORY = "1g"
INSTALL_PIDS = 512
APP_TMPFS_MB = 128
INSTALL_TMPFS_MB = 256
HELPER_TMPFS_MB = 16
NOBODY = "65534:65534"
STOP_GRACE = "2s"
"""Without `init: true` and a short grace, Node as PID 1 ignores SIGTERM and each `down` costs
10 s."""
LOG_LIMITS: Mapping[str, object] = {
    "driver": "json-file",
    "options": {"max-size": "10m", "max-file": "3"},
}
"""So a chatty app cannot fill your disk through the engine's logs. Per container, since an engine's
own settings are yours, and with the driver named, since these options mean nothing to another."""
HEALTH_TIMINGS: Mapping[str, str | int] = {
    "interval": "30s",
    "timeout": "10s",
    "retries": 3,
    "start_period": "120s",
    "start_interval": "250ms",
}
"""Fast while waiting, nothing while idle, and patient on a loaded machine: a check that succeeds
ends the start period, so a long one costs nothing when all is well."""
NO_ADDRESS_ON_THIS_MACHINE: Mapping[str, str] = {"com.docker.network.bridge.inhibit_ipv4": "true"}
"""For `sandbox`. An internal network's bridge holds an address of this machine's, and through it a
container reaches every service listening on all of this machine's addresses (measured on Linux,
Engine 29). With no address there, the network holds nothing of this machine's, and its containers
still reach each other."""
NO_IPV6 = False
"""`enable_ipv6` for `sandbox`, said outright: an engine set to give new networks IPv6 would
otherwise give the bridge an IPv6 address of this machine's, which `inhibit_ipv4` does not take
away."""
COMPLETED = {"condition": "service_completed_successfully"}
HEALTHY = {"condition": "service_healthy"}
EGRESS_TARGETS = (("1.1.1.1", 443), ("192.168.1.1", 80), ("10.0.0.1", 80), ("169.254.169.254", 80))
"""A public address, two LAN addresses and the cloud metadata address, which D11 must not reach."""
EGRESS_HOSTS_VARIABLE = "CSTUDY_EGRESS_HOSTS"
"""The IPv4 gateway of each of the stack's networks, comma-separated: known only once the stack
runs, so the probe reads them from its environment."""
EGRESS_HOST_PORTS = (22, 80, 443)
"""Where the probe tries each gateway. A refusal is this machine answering, so it reaches the
machine as much as a connection does."""
EGRESS_PROBE_TIMEOUT_S = 2
IPV6_LIST = "/proc/net/if_inet6"
IPV6_ADDRESS_CHECK = "\n".join(
    (
        "import ipaddress",
        "def foreign_ipv6(text):",
        "    found = []",
        "    for line in text.splitlines():",
        "        fields = line.split()",
        "        try:",
        "            address = ipaddress.IPv6Address(bytes.fromhex(fields[0]))",
        "        except (IndexError, ValueError):",
        "            continue",
        "        if not (address.is_loopback or address.is_link_local):",
        "            found.append(str(address))",
        "    return found",
    )
)
"""Every IPv6 address the kernel lists for the container but `::1` and `fe80::/10`: a global one
(`2000::/3`) or a unique local one (`fc00::/7`) is a route to this machine's bridge."""
EGRESS_PROBE = "\n".join(
    (
        IPV6_ADDRESS_CHECK,
        "import errno, os, socket, sys",
        f"socket.setdefaulttimeout({EGRESS_PROBE_TIMEOUT_S})",
        f"hosts = [h for h in os.environ.get({EGRESS_HOSTS_VARIABLE!r}, '').split(',') if h]",
        "answers = lambda to, codes: socket.socket().connect_ex(to) in codes",
        f"reached = [to for to in {EGRESS_TARGETS!r} if answers(to, (0,))]",
        f"machine = [(h, port) for h in hosts for port in {EGRESS_HOST_PORTS!r}]",
        "reached += [to for to in machine if answers(to, (0, errno.ECONNREFUSED))]",
        "try:",
        f"    text = open({IPV6_LIST!r}).read()",
        "except OSError:",
        "    text = ''",
        "addresses = foreign_ipv6(text)",
        "print('reached', reached, 'ipv6', addresses)",
        "sys.exit(1 if reached or addresses else 0)",
    )
)
"""Standard library only, run from the pinned Python image, on `sandbox` alone. A connection that
fails or times out proves what D11 asks; one that succeeds is named, and so is a refusal from this
machine."""

_DIGEST_LENGTH = 8
_STACK_NAME = re.compile(r"cstudy-[dtgi]-[a-z0-9][a-z0-9_-]*")


class StackKind(StrEnum):
    DEV = "dev"
    TEST = "test"
    GRADED = "graded"
    INSTALL = "install"

    @property
    def removes_volumes(self) -> bool:
        """A dev stack keeps its data, and an install stack its cache."""
        return self in (StackKind.TEST, StackKind.GRADED)

    @property
    def serves_the_grader(self) -> bool:
        """A test stack runs the visible cases and a graded stack all of them; a dev stack is
        yours, and publishes nothing for the grader."""
        return self in (StackKind.TEST, StackKind.GRADED)


_RUN_LETTERS: Mapping[StackKind, str] = {StackKind.TEST: "t", StackKind.GRADED: "g"}


def workspace_digest(root: str) -> str:
    """What the labels and the stable stack names call the workspace at `root`."""
    return hashlib.sha256(root.encode()).hexdigest()[:_DIGEST_LENGTH]


def run_stack_name(kind: StackKind, owner_pid: int, run_id: str) -> str:
    """A fresh name per run. It holds the owner, since a network or a volume carries no owner
    label, and a sweep must tell one being made from one left behind."""
    return f"cstudy-{_RUN_LETTERS[kind]}-{owner_pid}-{run_id}"


def dev_stack_name(slug: str, workspace: str) -> str:
    return f"cstudy-d-{slug}-{workspace}"


def install_stack_name(slug: str, workspace: str) -> str:
    return f"cstudy-i-{slug}-{workspace}"


def is_stack_name(name: str) -> bool:
    """Whether `name` has the form cstudy gives a stack, or a network or a volume compose named
    after one. A compose label says whatever the container's creator wrote: anything else is no
    stack of cstudy's, and reaches neither `docker compose -p` nor a path."""
    return _STACK_NAME.fullmatch(name) is not None


def _owner_in_name(stack: str) -> int | None:
    """The owner a run's name holds; None for a name of another form."""
    match stack.split("-"):
        case ["cstudy", letter, pid, *_] if letter in _RUN_LETTERS.values() and pid.isdigit():
            return int(pid)
        case _:
            return None


@dataclass(frozen=True, slots=True)
class StackIdentity:
    name: str
    """The compose project."""
    kind: StackKind
    workspace: str
    """`workspace_digest` of the workspace root."""
    slug: str
    owner_pid: int
    """The `cstudy` process that answers for the stack."""

    @property
    def stable_labels(self) -> dict[str, str]:
        """What a network and a volume carry."""
        return {
            LABEL_KIND: self.kind.value,
            LABEL_WORKSPACE: self.workspace,
            LABEL_SLUG: self.slug,
        }

    @property
    def container_labels(self) -> dict[str, str]:
        return {**self.stable_labels, LABEL_OWNER: str(self.owner_pid)}


@dataclass(frozen=True, slots=True)
class SandboxUser:
    uid: int
    gid: int

    @property
    def spec(self) -> str:
        return f"{self.uid}:{self.gid}"

    @property
    def passwd_line(self) -> str:
        """Without an entry, `whoami` fails and Node's `os.userInfo()` throws."""
        return f"cstudy:x:{self.uid}:{self.gid}:cstudy:{HOME_DIRECTORY}:/bin/sh\n"


@dataclass(frozen=True, slots=True)
class SandboxPaths:
    project: str
    """The project folder, absolute and with every link resolved."""
    run: str
    """`.cs/runs/<stack>/`, absolute: what the stack mounts from `cstudy` is copied here, since
    Docker Desktop silently mounts its own VM's folder for a path it does not share."""

    @property
    def devcontainer(self) -> str:
        return f"{self.project}/{DEVCONTAINER_DIRECTORY}"

    def in_run(self, name: str) -> str:
        return f"{self.run}/{name}"


@dataclass(frozen=True, slots=True)
class AppContainer:
    image: str
    command: tuple[str, ...] | None
    """`commands.run`, as the container's own command: its life is the app's. None idles, for an
    IDE or a debugger."""
    port: int
    environment: Mapping[str, str]
    """`project.env`; the fixed variables come on top."""
    mem_limit: str = APP_MEMORY
    health: str = "/health"
    """The path `cstudy` asks through the published port until it answers 2xx."""
    port_env: str = "PORT"
    """The variable the app reads for its port, for the message when it does not answer."""


@dataclass(frozen=True, slots=True)
class OneShot:
    """`bootstrap`: it runs after the services are up and before `app`, and a failure of it stops
    the start."""

    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GradeSetup:
    """`grade_setup`: a short-lived container with the project read-only, gone before `app`."""

    command: tuple[str, ...]
    grading_directory: str
    """`{problem}/grading` on this machine, which reaches this container only."""
    graded_level: int


@dataclass(frozen=True, slots=True)
class MockServerInput:
    """The mock server, as a stack takes it: the mock server's own code and config format are P5's
    (docs/specs/service-projects.md#mock-server)."""

    aliases: tuple[str, ...]
    """Each mock server's name, as a network alias of the one container."""
    control_token: str
    """Already in `rendered_config`; held here for the grader and for `commands.test`."""
    rendered_config: str
    """The JSON written to `.cs/runs/<run>/mocks.json` and mounted read-only."""


_NO_BACKING_SERVICES: Mapping[str, object] = {}


@dataclass(frozen=True, slots=True)
class BackingServices:
    """The problem's compose file (`project.services`), as a stack merges it
    (docs/specs/service-projects.md#backing-services)."""

    document: Mapping[str, object]
    """Parsed, and held to S21 before any stack is planned."""
    folder: str
    """The compose file's folder on this machine. What a bind mount names there reaches its service
    as a read-only copy under `.cs/runs/<stack>/services/`."""


@dataclass(frozen=True, slots=True)
class StackPlan:
    identity: StackIdentity
    user: SandboxUser
    paths: SandboxPaths
    app: AppContainer
    mocks: MockServerInput | None = None
    bootstrap: OneShot | None = None
    grade_setup: GradeSetup | None = None
    reset_prepare: OneShot | None = None
    """`commands.reset` with its `prepare` phase: once, after `bootstrap`, before `app`."""
    backing: BackingServices | None = None
    reach: tuple[str, ...] = ()
    """`project.grader_reach`: each `<name>:<port>` the grader may reach, as the app's network
    names it, published on `127.0.0.1` through the forwarder. A dev stack publishes none."""

    @property
    def backing_document(self) -> Mapping[str, object]:
        """The problem's compose file; an empty one without backing services."""
        return self.backing.document if self.backing is not None else _NO_BACKING_SERVICES


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """`commands.install` in a compose project of its own, which outlives the run with its cache:
    a `down -v` of a profile deletes a cache volume declared in the same file."""

    identity: StackIdentity
    user: SandboxUser
    paths: SandboxPaths
    image: str
    command: tuple[str, ...]
    environment: Mapping[str, str]


def stack_document(plan: StackPlan) -> dict[str, object]:
    """The compose file of a stack, with the problem's backing services merged into it."""
    services: dict[str, object] = {
        DATA_OWNER_SERVICE: _volume_owner(plan.identity, plan.user, DATA_VOLUME, DATA_DIRECTORY),
        APP_SERVICE: _app(plan),
        FORWARD_SERVICE: _forwarder(plan),
        EGRESS_PROBE_SERVICE: _egress_probe(plan),
    }
    if plan.grade_setup is not None:
        services[GRADE_SETUP_SERVICE] = _grade_setup(plan, plan.grade_setup)
    if plan.bootstrap is not None:
        services[BOOTSTRAP_SERVICE] = _bootstrap(plan, plan.bootstrap)
    if plan.reset_prepare is not None:
        services[RESET_PREPARE_SERVICE] = _reset_prepare(plan, plan.reset_prepare)
    if plan.mocks is not None:
        services[MOCK_SERVICE] = _mock_server(plan, plan.mocks)
    document = plan.backing_document
    for name, entry in backing_services_of(document).items():
        services[name] = _backing_service(plan, entry)
    labels = plan.identity.stable_labels
    sandbox = {
        "internal": True,
        "enable_ipv6": NO_IPV6,
        "driver_opts": NO_ADDRESS_ON_THIS_MACHINE,
        "labels": labels,
    }
    volumes = [DATA_VOLUME, *_backing_volumes_of(document)]
    return {
        "name": plan.identity.name,
        "services": services,
        "networks": {SANDBOX_NETWORK: sandbox, "edge": {"labels": labels}},
        "volumes": {volume: {"labels": labels} for volume in volumes},
    }


def backing_services_of(document: Mapping[str, object]) -> Mapping[str, Mapping[str, object]]:
    """The services of a problem's compose file, by name; none for a file that holds no mapping."""
    found = document.get("services")
    return cast(Mapping[str, Mapping[str, object]], found) if isinstance(found, Mapping) else {}


def _backing_volumes_of(document: Mapping[str, object]) -> tuple[str, ...]:
    found = document.get("volumes")
    return tuple(cast(Mapping[str, object], found)) if isinstance(found, Mapping) else ()


def backing_images(document: Mapping[str, object]) -> tuple[str, ...]:
    """What a stack pulls for the problem's backing services, in the file's order."""
    return tuple(str(entry.get("image")) for entry in backing_services_of(document).values())


def backing_bind_sources(document: Mapping[str, object]) -> tuple[str, ...]:
    """Every path a bind mount names, relative to the compose file's folder and without a leading
    `./`: what a stack copies under `.cs/runs/<stack>/services/`."""
    sources = (
        volume_source(volume)
        for entry in backing_services_of(document).values()
        for volume in _mounts_of(entry)
    )
    return tuple(_relative(source) for source, is_bind in sources if source and is_bind)


def volume_source(volume: object) -> tuple[str | None, bool]:
    """What a compose volume entry mounts, and whether that is a path on this machine; None for an
    anonymous volume."""
    if isinstance(volume, Mapping):
        entry = cast(Mapping[str, object], volume)
        source = entry.get("source")
        return (str(source) if source is not None else None), entry.get("type") == "bind"
    source, separator, _target = str(volume).partition(":")
    if not separator:
        return None, False
    return source, source.startswith((".", "/", "~"))


def _mounts_of(entry: Mapping[str, object]) -> Sequence[object]:
    return cast(Sequence[object], entry.get("volumes") or ())


def _relative(source: str) -> str:
    return source.removeprefix("./")


def reach_listen_ports(plan: StackPlan) -> dict[str, int]:
    """Where the forwarder listens for each service the grader may reach: ports of its own, clear
    of the app's and the control port."""
    taken = {plan.app.port, CONTROL_PORT}
    free = (port for port in itertools.count(REACH_FIRST_PORT) if port not in taken)
    return {origin: next(free) for origin in plan.reach}


def install_document(plan: InstallPlan) -> dict[str, object]:
    """The compose file of `commands.install`, which may reach the network, and so your LAN and
    this machine's loopback services, with nothing else in the stack."""
    labels = plan.identity.stable_labels
    install = {
        **_hardened(plan.identity),
        "image": plan.image,
        "user": plan.user.spec,
        "working_dir": plan.paths.project,
        "command": list(plan.command),
        "environment": {
            "HOME": HOME_DIRECTORY,
            "TMPDIR": TEMPORARY_DIRECTORY,
            **plan.environment,
        },
        "tmpfs": [_tmpfs(INSTALL_TMPFS_MB, plan.user)],
        "volumes": [*_project_mounts(plan.paths), f"cache:{CACHE_DIRECTORY}"],
        "networks": ["egress"],
        "mem_limit": INSTALL_MEMORY,
        "pids_limit": INSTALL_PIDS,
        "depends_on": {CACHE_OWNER_SERVICE: COMPLETED},
    }
    return {
        "name": plan.identity.name,
        "services": {
            CACHE_OWNER_SERVICE: _volume_owner(plan.identity, plan.user, "cache", CACHE_DIRECTORY),
            INSTALL_SERVICE: install,
        },
        "networks": {"egress": {"labels": labels}},
        "volumes": {"cache": {"labels": labels}},
    }


def render_compose(document: Mapping[str, object]) -> str:
    """JSON, which compose reads as YAML, with every `$` doubled so nothing is interpolated."""
    return json.dumps(_without_interpolation(document), indent=2) + "\n"


def _without_interpolation(value: object) -> object:
    if isinstance(value, str):
        return value.replace("$", "$$")
    if isinstance(value, Mapping):
        entries = cast(Mapping[str, object], value)
        return {key: _without_interpolation(found) for key, found in entries.items()}
    if isinstance(value, list | tuple):
        return [_without_interpolation(found) for found in cast(Iterable[object], value)]
    return value


def _hardened(identity: StackIdentity) -> dict[str, object]:
    return {
        "init": True,
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": [NO_NEW_PRIVILEGES],
        "stop_grace_period": STOP_GRACE,
        "logging": LOG_LIMITS,
        "labels": identity.container_labels,
    }


def _tmpfs(size_mb: int, user: SandboxUser) -> str:
    return f"{TEMPORARY_DIRECTORY}:size={size_mb}m,uid={user.uid},gid={user.gid},mode=1777"


def _bind(source: str, target: str, *, read_only: bool = False) -> dict[str, object]:
    mount: dict[str, object] = {"type": "bind", "source": source, "target": target}
    return {**mount, "read_only": True} if read_only else mount


def _project_mounts(paths: SandboxPaths) -> list[object]:
    return [
        _bind(paths.project, paths.project),
        _bind(paths.devcontainer, paths.devcontainer, read_only=True),
        _bind(paths.in_run(PASSWD_FILE), "/etc/passwd", read_only=True),
    ]


def _volume_owner(
    identity: StackIdentity, user: SandboxUser, volume: str, target: str
) -> dict[str, object]:
    """A fresh named volume is root's, so a one-off with `CAP_CHOWN` alone hands it to the user."""
    return {
        **_hardened(identity),
        "image": PYTHON_IMAGE,
        "command": ["chown", user.spec, target],
        "network_mode": "none",
        "cap_add": ["CHOWN"],
        "mem_limit": OWNER_MEMORY,
        "pids_limit": OWNER_PIDS,
        "volumes": [f"{volume}:{target}"],
    }


def _app_environment(environment: Mapping[str, str]) -> dict[str, str]:
    return {
        **environment,
        "CSTUDY_DATA_DIR": DATA_DIRECTORY,
        "HOME": HOME_DIRECTORY,
        "TMPDIR": TEMPORARY_DIRECTORY,
    }


def _app_like(plan: StackPlan) -> dict[str, object]:
    """What `app` and the one-offs of its image share."""
    return {
        **_hardened(plan.identity),
        "image": plan.app.image,
        "user": plan.user.spec,
        "working_dir": plan.paths.project,
        "environment": _app_environment(plan.app.environment),
        "tmpfs": [_tmpfs(APP_TMPFS_MB, plan.user)],
        "volumes": [*_project_mounts(plan.paths), f"data:{DATA_DIRECTORY}"],
        "networks": [SANDBOX_NETWORK],
        "mem_limit": plan.app.mem_limit,
        "pids_limit": APP_PIDS,
    }


def _ready_for_commands(plan: StackPlan) -> dict[str, object]:
    """What every command of the app's image waits for: its data, the mock servers, which it may
    call as it starts, and each backing service's healthcheck."""
    needs: dict[str, object] = {DATA_OWNER_SERVICE: COMPLETED}
    if plan.mocks is not None:
        needs[MOCK_SERVICE] = HEALTHY
    document = plan.backing_document
    for name in backing_services_of(document):
        needs[name] = HEALTHY
    return needs


def _after(plan: StackPlan, *earlier: tuple[str, object | None]) -> dict[str, object]:
    """`_ready_for_commands`, then the nearest one-shot that is declared: each waits for the one
    before it, so a failure stops what comes after and every one-shot has a service depending on
    it, which `up --wait` needs."""
    needs = _ready_for_commands(plan)
    declared = next((name for name, one_shot in earlier if one_shot is not None), None)
    return needs if declared is None else {**needs, declared: COMPLETED}


def _app(plan: StackPlan) -> dict[str, object]:
    """`app` has no compose healthcheck: its image may hold no client to probe with, so
    `cstudy` asks the health path through the published port and reads the container's state, for
    any language alike."""
    depends_on = _after(
        plan,
        (RESET_PREPARE_SERVICE, plan.reset_prepare),
        (BOOTSTRAP_SERVICE, plan.bootstrap),
        (GRADE_SETUP_SERVICE, plan.grade_setup),
    )
    command = plan.app.command if plan.app.command is not None else ("sleep", "infinity")
    return {**_app_like(plan), "command": list(command), "depends_on": depends_on}


def _bootstrap(plan: StackPlan, bootstrap: OneShot) -> dict[str, object]:
    depends_on = _after(plan, (GRADE_SETUP_SERVICE, plan.grade_setup))
    return {**_app_like(plan), "command": list(bootstrap.command), "depends_on": depends_on}


def _reset_prepare(plan: StackPlan, prepare: OneShot) -> dict[str, object]:
    return {
        **_app_like(plan),
        "command": list(prepare.command),
        "environment": {
            **_app_environment(plan.app.environment),
            RESET_PHASE_VARIABLE: RESET_PHASE_PREPARE,
        },
        "depends_on": _after(
            plan, (BOOTSTRAP_SERVICE, plan.bootstrap), (GRADE_SETUP_SERVICE, plan.grade_setup)
        ),
    }


def _grade_setup(plan: StackPlan, setup: GradeSetup) -> dict[str, object]:
    paths = plan.paths
    return {
        **_app_like(plan),
        "command": list(setup.command),
        "environment": {
            **_app_environment(plan.app.environment),
            "CSTUDY_PROBLEM_DIR": PROBLEM_DIRECTORY,
            "CSTUDY_GRADED_LEVEL": str(setup.graded_level),
        },
        "volumes": [
            _bind(paths.project, paths.project, read_only=True),
            _bind(setup.grading_directory, f"{PROBLEM_DIRECTORY}/grading", read_only=True),
            _bind(paths.in_run(PASSWD_FILE), "/etc/passwd", read_only=True),
            f"data:{DATA_DIRECTORY}",
        ],
        "depends_on": _ready_for_commands(plan),
    }


def _helper(identity: StackIdentity) -> dict[str, object]:
    """The mock server and the forwarder: `cstudy`'s own code, as nobody."""
    return {
        **_hardened(identity),
        "image": PYTHON_IMAGE,
        "user": NOBODY,
        "tmpfs": [f"{TEMPORARY_DIRECTORY}:size={HELPER_TMPFS_MB}m,mode=1777"],
        "mem_limit": HELPER_MEMORY,
        "pids_limit": HELPER_PIDS,
    }


def _listens(port: int) -> dict[str, object]:
    probe = f"import socket;socket.create_connection(('127.0.0.1',{port}),1)"
    return {"test": ["CMD", "python", "-I", "-c", probe], **HEALTH_TIMINGS}


def _mock_server(plan: StackPlan, mocks: MockServerInput) -> dict[str, object]:
    paths = plan.paths
    return {
        **_helper(plan.identity),
        "command": list(MOCK_COMMAND),
        "environment": {"HOME": TEMPORARY_DIRECTORY},
        "volumes": [
            _bind(paths.in_run(MOCK_CODE_DIRECTORY), MOCK_CODE_PATH, read_only=True),
            _bind(paths.in_run(MOCK_CONFIG_FILE), MOCK_CONFIG_PATH, read_only=True),
        ],
        "networks": {SANDBOX_NETWORK: {"aliases": list(mocks.aliases)}},
        "healthcheck": _listens(CONTROL_PORT),
    }


def _backing_service(plan: StackPlan, entry: Mapping[str, object]) -> dict[str, object]:
    """The problem's settings that `BACKING_SERVICE_FIELDS` allows, inside the stack's own: an
    engine such as Postgres keeps its own user and writable paths, and holds no capability, gains
    no privilege and reaches nothing beyond `sandbox`. A read-only root is the default, which the
    problem may turn off for an image that writes outside its volumes and tmpfs."""
    allowed = {field: value for field, value in entry.items() if field in BACKING_SERVICE_FIELDS}
    service: dict[str, object] = {
        "read_only": True,
        **allowed,
        "cap_drop": ["ALL"],
        "security_opt": [NO_NEW_PRIVILEGES],
        "logging": LOG_LIMITS,
        "labels": plan.identity.container_labels,
        "networks": [SANDBOX_NETWORK],
    }
    if "volumes" in allowed:
        service["volumes"] = [_backing_mount(plan.paths, mount) for mount in _mounts_of(entry)]
    return service


def _backing_mount(paths: SandboxPaths, mount: object) -> object:
    """A bind mount becomes a read-only mount of its copy under the run's folder; a named volume
    and a tmpfs stay as written."""
    source, is_bind = volume_source(mount)
    if source is None or not is_bind:
        return mount
    if isinstance(mount, Mapping):
        target = str(cast(Mapping[str, object], mount).get("target"))
    else:
        target = str(mount).split(":")[1]
    copy = paths.in_run(f"{SERVICE_FILES_DIRECTORY}/{_relative(source)}")
    return _bind(copy, target, read_only=True)


def _egress_probe(plan: StackPlan) -> dict[str, object]:
    """On `sandbox` alone, as the app is. A profile keeps it out of `up`, and only D11 runs it."""
    return {
        **_helper(plan.identity),
        "profiles": [EGRESS_PROBE_SERVICE],
        "command": ["python", "-I", "-c", EGRESS_PROBE],
        "environment": {"HOME": TEMPORARY_DIRECTORY},
        "networks": [SANDBOX_NETWORK],
    }


def _forwarder(plan: StackPlan) -> dict[str, object]:
    """A service only on an internal network cannot publish a port: `docker compose port` prints
    `:0` and exits 0. This relay holds no user code and joins both networks."""
    port = plan.app.port
    relays = [f"{port}={APP_SERVICE}:{port}"]
    published = [f"127.0.0.1::{port}"]
    if plan.mocks is not None:
        relays.append(f"{CONTROL_PORT}={MOCK_SERVICE}:{CONTROL_PORT}")
        published.append(f"127.0.0.1::{CONTROL_PORT}")
    for origin, listen in reach_listen_ports(plan).items():
        relays.append(f"{listen}={origin}")
        published.append(f"127.0.0.1::{listen}")
    return {
        **_helper(plan.identity),
        "command": ["python", "-I", FORWARDER_PATH, *relays],
        "environment": {"HOME": TEMPORARY_DIRECTORY},
        "volumes": [_bind(plan.paths.in_run(FORWARDER_FILE), FORWARDER_PATH, read_only=True)],
        "networks": [SANDBOX_NETWORK, "edge"],
        "ports": published,
        "healthcheck": _listens(port),
    }


@dataclass(frozen=True, slots=True)
class StackContainer:
    """A container cstudy's labels name, as `docker ps` lists it."""

    stack: str
    kind: str
    workspace: str
    owner_pid: int | None
    """None when the label is missing or does not read as a number."""


@dataclass(frozen=True, slots=True)
class StackResource:
    """A network or a volume cstudy's labels name."""

    name: str
    stack: str
    kind: str
    workspace: str


@dataclass(frozen=True, slots=True)
class SandboxInventory:
    """Everything that carries cstudy's labels, and nothing that does not. Anyone can write those
    labels, so `leftovers_in` trusts only a name of cstudy's own form."""

    containers: tuple[StackContainer, ...] = ()
    networks: tuple[StackResource, ...] = ()
    volumes: tuple[StackResource, ...] = ()


@dataclass(frozen=True, slots=True)
class LeftoverStack:
    name: str
    workspace: str
    removes_volumes: bool


@dataclass(frozen=True, slots=True)
class Leftovers:
    stacks: tuple[LeftoverStack, ...] = ()
    networks: tuple[str, ...] = ()
    volumes: tuple[str, ...] = ()

    @property
    def count(self) -> int:
        return len(self.stacks) + len(self.networks) + len(self.volumes)

    def __bool__(self) -> bool:
        return self.count > 0


def leftovers_in(
    inventory: SandboxInventory,
    is_alive: Callable[[int], bool],
    workspace: str | None = None,
) -> Leftovers:
    """The stacks with no live owner, whole, and the networks and volumes of a dead run with no
    container left. A run's own volumes and networks go with a `down`, and an anonymous volume
    only that way, so a container is never removed alone. A dev stack's data and an install's
    cache are not leftovers. A name that is not `is_stack_name` is no leftover at all. `workspace`
    None looks at every workspace."""
    containers = _of_workspace(inventory.containers, workspace)
    by_stack: dict[str, list[StackContainer]] = {}
    for found in containers:
        if is_stack_name(found.stack):
            by_stack.setdefault(found.stack, []).append(found)
    stacks = tuple(
        LeftoverStack(stack, found[0].workspace, _removes_volumes(found[0].kind))
        for stack, found in sorted(by_stack.items())
        if not any(_lives(container.owner_pid, is_alive) for container in found)
    )
    used = frozenset(container.stack for container in inventory.containers)
    return Leftovers(
        stacks,
        _strays(_of_workspace(inventory.networks, workspace), used, is_alive),
        _strays(_of_workspace(inventory.volumes, workspace), used, is_alive),
    )


def _of_workspace[T: StackContainer | StackResource](
    found: tuple[T, ...], workspace: str | None
) -> list[T]:
    return [entry for entry in found if workspace is None or entry.workspace == workspace]


def _lives(pid: int | None, is_alive: Callable[[int], bool]) -> bool:
    return pid is not None and is_alive(pid)


def _removes_volumes(kind: str) -> bool:
    """A kind this `cstudy` does not know keeps its volumes."""
    return kind in (StackKind.TEST, StackKind.GRADED)


def _strays(
    resources: list[StackResource], used: frozenset[str], is_alive: Callable[[int], bool]
) -> tuple[str, ...]:
    return tuple(
        sorted(
            resource.name
            for resource in resources
            if is_stack_name(resource.stack)
            and is_stack_name(resource.name)
            and resource.stack not in used
            and _removes_volumes(resource.kind)
            and not _lives(_owner_in_name(resource.stack), is_alive)
        )
    )


class StartupFailure(StrEnum):
    """Why a stack did not become ready: none of these is a result of a test or a case."""

    SERVICE = "service"
    """A container of `cstudy`'s or of the problem's, or the startup budget ran out."""
    BOOTSTRAP = "bootstrap"
    GRADE_SETUP = "grade_setup"
    APP_EXITED = "app_exited"
    HEALTH_TIMEOUT = "health_timeout"

    @property
    def is_your_code(self) -> bool:
        """Exit 2, as code that does not load; the others exit 4."""
        return self in (
            StartupFailure.BOOTSTRAP,
            StartupFailure.APP_EXITED,
            StartupFailure.HEALTH_TIMEOUT,
        )


class StackStartError(SandboxError):
    """The stack did not become ready within its startup budget, or a part of it failed. Raised
    with the logs read and before the stack is taken down."""

    def __init__(self, failure: StartupFailure, message: str, output: str = "") -> None:
        super().__init__(message)
        self.failure = failure
        self.output = output


STARTUP_UP_S = 300
"""`up --wait`, `grade_setup` and `bootstrap` included: minutes on a loaded machine, and it says so
when it runs out. `project.timeouts_s.startup` raises it for a heavy problem."""
DEFAULT_READY_S = 60
"""From `up --wait` to the first 2xx from the health path, unless `app.ready_timeout_s` says."""


@dataclass(frozen=True, slots=True)
class StartupBudget:
    """The first clock: how long a stack may take to become ready. It is spent before any limit on
    a test or a case starts, and running out of it changes no result."""

    up_s: int = STARTUP_UP_S
    app_ready_s: int = DEFAULT_READY_S


@dataclass(frozen=True, slots=True)
class ReadyStack:
    """A stack whose app answered its health path, and the moment it did. Every limit, hang guard
    and reported run time starts at `ready_at`; a total may count from `started_at`."""

    name: str
    app_port: int
    """On `127.0.0.1`, through the forwarder."""
    control_port: int | None
    """The mock control port, on `127.0.0.1`; None without mock servers."""
    started_at: float
    ready_at: float
    """In the seconds of `Clock.monotonic`."""
    reach_ports: Mapping[str, int] = field(default_factory=dict[str, int])
    """The port on `127.0.0.1` of each `<name>:<port>` the grader may reach."""

    @property
    def startup_seconds(self) -> float:
        return self.ready_at - self.started_at

    @property
    def reach_urls(self) -> dict[str, str]:
        """`http://127.0.0.1:<port>` by the `<name>:<port>` the app's network knows it by: a
        client dials the URL and keeps that name as its `Host`."""
        return {origin: f"http://127.0.0.1:{port}" for origin, port in self.reach_ports.items()}

    @property
    def app_url(self) -> str:
        return f"http://127.0.0.1:{self.app_port}"

    @property
    def control_url(self) -> str | None:
        return None if self.control_port is None else f"http://127.0.0.1:{self.control_port}"


@dataclass(frozen=True, slots=True)
class CommandOutcome:
    """A command that ran in a container."""

    exit_code: int
    output: str = field(repr=False)
    """Standard output and standard error, combined."""
    timed_out: bool = False
