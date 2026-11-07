"""`SandboxEngine` over the Docker command line (docs/specs/service-projects.md#sandbox).

Every call runs with standard input at end of file, and never with `-y`: a label that changes on a
volume makes compose ask whether to recreate it, which hangs on an open pipe and loses the data
under `-y`. Readiness is `docker info`, which starts nothing and wakes no idle VM, never `docker
desktop status`, which said `stopped` while the engine answered, and never `docker system df`,
which wakes the VM.
"""

import http.client
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import IO, Protocol, cast

from coding_study.adapters.process_environment import docker_environment
from coding_study.adapters.process_liveness import is_alive
from coding_study.adapters.project_folders import clear_setuid_bits
from coding_study.adapters.stack_guard import DOCKER, StackGuard
from coding_study.application.ports import ContainerCommand, ProbeResult, ProgressNotice
from coding_study.domain.docker_engine import (
    DID_NOT_START,
    MACOS_PLATFORM,
    SYSTEM_ENGINE_STOPPED,
    EngineState,
    EngineStatus,
)
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    APP_SERVICE,
    BOOTSTRAP_SERVICE,
    CONTROL_PORT,
    FORWARD_SERVICE,
    FORWARDER_FILE,
    GRADE_SETUP_SERVICE,
    INSTALL_SERVICE,
    LABEL_KIND,
    LABEL_OWNER,
    LABEL_PROJECT,
    LABEL_WORKSPACE,
    MOCK_CODE_DIRECTORY,
    MOCK_CONFIG_FILE,
    PASSWD_FILE,
    STACK_FILE,
    CommandOutcome,
    InstallPlan,
    LeftoverStack,
    ReadyStack,
    SandboxInventory,
    SandboxPaths,
    SandboxUser,
    StackContainer,
    StackIdentity,
    StackPlan,
    StackResource,
    StackStartError,
    StartupBudget,
    StartupFailure,
    install_document,
    render_compose,
    stack_document,
)

ENGINE_START_S = 120
ENGINE_QUERY_S = 30.0
ENGINE_POLL_S = 0.5
STOP_TIMEOUT_S = 120.0
INVENTORY_TIMEOUT_S = 60.0
PULL_TIMEOUT_S = 1800.0
UP_GRACE_S = 30
"""Past compose's own `--wait-timeout`, so its message arrives before the process is killed."""
HEALTH_POLL_S = 0.1
HEALTH_PROBE_TIMEOUT_S = 5.0
STATE_CHECK_EVERY_S = 1.0
LOG_LINES = 200
TAIL_BYTES = 4096
TIMED_OUT_EXIT_CODE = 124
NOT_EXECUTABLE_EXIT_CODE = 126
READ_GRACE_S = 5.0
LOOPBACK = "127.0.0.1"
HTTP_OK_FIRST = 200
HTTP_OK_LAST = 299
READABLE_FILE = 0o644
READABLE_DIRECTORY = 0o755
_COMPOSE = (DOCKER, "compose", "--ansi", "never")
_PULL_NEVER = ("--pull", "never")
_LABEL_FILTER = ("--filter", f"label={LABEL_KIND}")
_RESOURCE_FORMAT = "\t".join(
    (
        "{{.Name}}",
        f'{{{{.Label "{LABEL_PROJECT}"}}}}',
        f'{{{{.Label "{LABEL_KIND}"}}}}',
        f'{{{{.Label "{LABEL_WORKSPACE}"}}}}',
    )
)
_CONTAINER_FORMAT = "\t".join(
    (
        f'{{{{.Label "{LABEL_PROJECT}"}}}}',
        f'{{{{.Label "{LABEL_KIND}"}}}}',
        f'{{{{.Label "{LABEL_WORKSPACE}"}}}}',
        f'{{{{.Label "{LABEL_OWNER}"}}}}',
    )
)
_NOT_YOUR_CODE = "This says nothing about your code, and no result changes."
_FORWARDER_SOURCE = Path(__file__).with_name("sandbox_forward.py")
_MOCK_CODE_SOURCE = Path(__file__).with_name(MOCK_CODE_DIRECTORY)
_PERMISSION_REFUSED = "permission denied"

type HealthProbe = Callable[[int, str], bool]


class DockerRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        timeout_s: float | None = None,
        on_line: Callable[[str], None] | None = None,
    ) -> ProbeResult | None:
        """Runs a command to its end with standard input at end of file; None when the executable
        is missing, and `TIMED_OUT_EXIT_CODE` when `timeout_s` ran out, with the process killed."""
        ...


class SubprocessDockerRunner:
    """Runs the Docker client in a process group of its own, so its plugin goes with it."""

    def run(
        self,
        command: Sequence[str],
        timeout_s: float | None = None,
        on_line: Callable[[str], None] | None = None,
    ) -> ProbeResult | None:
        try:
            process = subprocess.Popen(
                list(command),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                env=docker_environment(),
                start_new_session=True,
            )
        except FileNotFoundError:
            return None
        except OSError as error:
            return ProbeResult(NOT_EXECUTABLE_EXIT_CODE, str(error))
        return _finished(process, timeout_s, on_line)


def _finished(
    process: subprocess.Popen[str],
    timeout_s: float | None,
    on_line: Callable[[str], None] | None,
) -> ProbeResult:
    lines: list[str] = []
    assert process.stdout is not None
    reader = threading.Thread(target=_collect, args=(process.stdout, lines, on_line), daemon=True)
    reader.start()
    try:
        process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _kill_group(process)
        reader.join(READ_GRACE_S)
        return ProbeResult(TIMED_OUT_EXIT_CODE, "".join(lines))
    except BaseException:
        _kill_group(process)
        raise
    reader.join(READ_GRACE_S)
    return ProbeResult(process.returncode, "".join(lines))


def _collect(stream: IO[str], lines: list[str], on_line: Callable[[str], None] | None) -> None:
    for line in stream:
        lines.append(line)
        if on_line is not None:
            on_line(line.rstrip("\n"))


def _kill_group(process: subprocess.Popen[str]) -> None:
    with suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def default_docker_runner() -> DockerRunner:
    """What `DockerSandbox` runs commands with; the tests replace this one function, so that no
    fast test ever reaches a real engine."""
    return SubprocessDockerRunner()


def http_health(port: int, path: str) -> bool:
    """Asks `127.0.0.1` directly: no proxy from the environment, and no redirect followed."""
    connection = http.client.HTTPConnection(LOOPBACK, port, timeout=HEALTH_PROBE_TIMEOUT_S)
    try:
        connection.request("GET", path)
        return HTTP_OK_FIRST <= connection.getresponse().status <= HTTP_OK_LAST
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


class DockerSandbox:
    def __init__(
        self,
        runner: DockerRunner | None = None,
        *,
        runs_directory: Path | None = None,
        health_probe: HealthProbe = http_health,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        platform: str = sys.platform,
    ) -> None:
        self._runner = runner or default_docker_runner()
        self._runs_directory = runs_directory
        self._health_probe = health_probe
        self._monotonic = monotonic
        self._sleep = sleep
        self._platform = platform

    def state(self) -> EngineState:
        info = self._runner.run((DOCKER, "info", "--format", "{{.ServerVersion}}"), ENGINE_QUERY_S)
        if info is None:
            return EngineState(EngineStatus.NOT_INSTALLED)
        version = info.output.strip()
        if info.exit_code != 0 or not version:
            return EngineState(_refused_or_stopped(info.output))
        compose = self._runner.run((DOCKER, "compose", "version", "--short"), ENGINE_QUERY_S)
        if compose is None or compose.exit_code != 0:
            return EngineState(EngineStatus.NO_COMPOSE, version)
        return EngineState(EngineStatus.RUNNING, version, compose.output.strip())

    def platform(self) -> str:
        return self._platform

    def start_engine(self, notify: ProgressNotice) -> None:
        notify("starting Docker ...")
        for command in _start_commands(self._platform):
            started = self._runner.run(command, ENGINE_QUERY_S)
            if started is not None and started.exit_code == 0:
                self._wait_for_engine()
                return
        raise SandboxError(
            DID_NOT_START if self._platform == MACOS_PLATFORM else SYSTEM_ENGINE_STOPPED
        )

    def _wait_for_engine(self) -> None:
        deadline = self._monotonic() + ENGINE_START_S
        while self._monotonic() < deadline:
            info = self._runner.run(
                (DOCKER, "info", "--format", "{{.ServerVersion}}"), ENGINE_QUERY_S
            )
            if info is not None and info.exit_code == 0:
                return
            self._sleep(ENGINE_POLL_S)
        raise SandboxError(f"Docker did not answer within {ENGINE_START_S} s of starting it")

    def image_present(self, image: str) -> bool:
        found = self._runner.run((DOCKER, "image", "inspect", "--format", "{{.Id}}", image))
        return found is not None and found.exit_code == 0

    def pull(self, image: str, notify: ProgressNotice) -> None:
        pulled = self._runner.run((DOCKER, "pull", image), PULL_TIMEOUT_S, notify)
        if pulled is None or pulled.exit_code != 0:
            output = pulled.output if pulled is not None else ""
            raise SandboxError(
                f"could not pull {image}: {_tail(output).strip()}\n"
                "If you are offline, connect to the network and run the command again."
            )

    def inventory(self) -> SandboxInventory:
        containers = self._listing(
            (DOCKER, "ps", "-a", *_LABEL_FILTER, "--format", _CONTAINER_FORMAT)
        )
        networks = self._listing(
            (DOCKER, "network", "ls", *_LABEL_FILTER, "--format", _RESOURCE_FORMAT)
        )
        volumes = self._listing(
            (DOCKER, "volume", "ls", *_LABEL_FILTER, "--format", _RESOURCE_FORMAT)
        )
        return SandboxInventory(
            tuple(_container(line) for line in containers),
            tuple(_resource(line) for line in networks),
            tuple(_resource(line) for line in volumes),
        )

    def _listing(self, command: tuple[str, ...]) -> list[str]:
        found = self._runner.run(command, INVENTORY_TIMEOUT_S)
        if found is None or found.exit_code != 0:
            output = found.output.strip() if found is not None else "docker is not installed"
            raise SandboxError(f"could not list what cstudy started: {output}")
        return found.output.splitlines()

    def is_alive(self, pid: int) -> bool:
        return is_alive(pid)

    def remove_stack(self, stack: LeftoverStack) -> bool:
        removed = self._down(stack.name, stack.removes_volumes)
        if removed and self._runs_directory is not None:
            _remove_folder(self._runs_directory / stack.name)
        return removed

    def remove_network(self, name: str) -> bool:
        return self._succeeded((DOCKER, "network", "rm", name))

    def remove_volume(self, name: str) -> bool:
        return self._succeeded((DOCKER, "volume", "rm", name))

    def _succeeded(self, command: tuple[str, ...]) -> bool:
        result = self._runner.run(command, INVENTORY_TIMEOUT_S)
        return result is not None and result.exit_code == 0

    @contextmanager
    def guard(self, identity: StackIdentity) -> Generator[None]:
        with StackGuard(
            identity.name,
            removes_volumes=identity.kind.removes_volumes,
            environment=docker_environment(),
        ):
            yield

    def start(self, plan: StackPlan, budget: StartupBudget) -> ReadyStack:
        started_at = self._monotonic()
        _prepare_project(plan.paths)
        _write_stack_files(plan)
        up = self._compose(
            plan,
            ("up", "--wait", "--wait-timeout", str(budget.up_s), *_PULL_NEVER),
            budget.up_s + UP_GRACE_S,
        )
        if up is None:
            raise SandboxError("docker is not installed")
        if up.exit_code != 0:
            raise self._failed_up(plan, up, budget)
        app_port = self._published(plan, plan.app.port)
        control_port = self._published(plan, CONTROL_PORT) if plan.mocks is not None else None
        if plan.app.command is not None:
            self._wait_for_health(plan, app_port, budget)
        return ReadyStack(plan.identity.name, app_port, control_port, started_at, self._monotonic())

    def _compose(
        self,
        plan: StackPlan | InstallPlan,
        arguments: tuple[str, ...],
        timeout_s: float | None,
        on_line: Callable[[str], None] | None = None,
    ) -> ProbeResult | None:
        command = (
            *_COMPOSE,
            "-p",
            plan.identity.name,
            "-f",
            plan.paths.in_run(STACK_FILE),
            *arguments,
        )
        return self._runner.run(command, timeout_s, on_line)

    def _published(self, plan: StackPlan, port: int) -> int:
        """`docker compose port` prints `:0` and exits 0 for a service that published nothing."""
        answer = self._compose(plan, ("port", FORWARD_SERVICE, str(port)), ENGINE_QUERY_S)
        found = _loopback_port(answer.output) if answer and answer.exit_code == 0 else None
        if found is None:
            text = answer.output.strip() if answer else "docker is not installed"
            raise StackStartError(
                StartupFailure.SERVICE,
                f"the stack published no port on {LOOPBACK} for {port} ({text}). {_NOT_YOUR_CODE}",
            )
        return found

    def _wait_for_health(self, plan: StackPlan, port: int, budget: StartupBudget) -> None:
        """Until the app's health path answers 2xx. Reads the container's state about once a
        second, so an app that crashed fails at once and not at the end of the budget."""
        deadline = self._monotonic() + budget.app_ready_s
        next_state_check = self._monotonic()
        while not self._health_probe(port, plan.app.health):
            now = self._monotonic()
            if now >= next_state_check:
                self._require_app_running(plan)
                next_state_check = now + STATE_CHECK_EVERY_S
            if now >= deadline:
                raise self._health_timeout(plan, port, budget)
            self._sleep(HEALTH_POLL_S)

    def _require_app_running(self, plan: StackPlan) -> None:
        state = self._service_states(plan).get(APP_SERVICE)
        if state is not None and state.exited:
            raise self._app_exited(plan, state.exit_code)

    def _app_exited(self, plan: StackPlan, exit_code: int) -> StackStartError:
        return StackStartError(
            StartupFailure.APP_EXITED,
            f"your app exited with code {exit_code} before it answered {plan.app.health}",
            self._logs(plan, APP_SERVICE),
        )

    def _health_timeout(self, plan: StackPlan, port: int, budget: StartupBudget) -> StackStartError:
        app = plan.app
        return StackStartError(
            StartupFailure.HEALTH_TIMEOUT,
            f"http://{LOOPBACK}:{port}{app.health} did not answer 2xx within "
            f"{budget.app_ready_s} s. Your app must read {app.port_env} and listen on all "
            "interfaces inside the container (0.0.0.0), not 127.0.0.1.",
            self._logs(plan, APP_SERVICE),
        )

    def _failed_up(
        self, plan: StackPlan, up: ProbeResult, budget: StartupBudget
    ) -> StackStartError:
        states = self._service_states(plan)
        app = states.get(APP_SERVICE)
        if (setup := states.get(GRADE_SETUP_SERVICE)) and setup.failed:
            return StackStartError(
                StartupFailure.GRADE_SETUP,
                "grade_setup failed: the problem is at fault, not your code",
            )
        if (bootstrap := states.get(BOOTSTRAP_SERVICE)) and bootstrap.failed:
            return StackStartError(
                StartupFailure.BOOTSTRAP,
                f"bootstrap exited with code {bootstrap.exit_code}",
                self._logs(plan, BOOTSTRAP_SERVICE),
            )
        if app is not None and app.exited:
            return self._app_exited(plan, app.exit_code)
        return StackStartError(StartupFailure.SERVICE, _service_failure(up, budget))

    def _service_states(self, plan: StackPlan) -> dict[str, "_ServiceState"]:
        listed = self._compose(plan, ("ps", "-a", "--format", "json"), ENGINE_QUERY_S)
        if listed is None or listed.exit_code != 0:
            return {}
        return _parsed_states(listed.output)

    def _logs(self, plan: StackPlan, service: str) -> str:
        logs = self._compose(
            plan,
            ("logs", "--no-color", "--no-log-prefix", "--tail", str(LOG_LINES), service),
            ENGINE_QUERY_S,
        )
        return _tail(logs.output) if logs is not None else ""

    def stop(self, plan: StackPlan) -> str | None:
        return self._stopped(plan.identity, plan.paths)

    def stop_install(self, plan: InstallPlan) -> str | None:
        return self._stopped(plan.identity, plan.paths)

    def _stopped(self, identity: StackIdentity, paths: SandboxPaths) -> str | None:
        down = self._down(identity.name, identity.kind.removes_volumes)
        clear_setuid_bits(Path(paths.project))
        if not down:
            return f"could not take {identity.name} down; the next run or doctor --fix will"
        _remove_folder(Path(paths.run))
        return None

    def _down(self, name: str, removes_volumes: bool) -> bool:
        flags = ("-v",) if removes_volumes else ()
        down = self._runner.run((*_COMPOSE, "-p", name, "down", *flags), STOP_TIMEOUT_S)
        return down is not None and down.exit_code == 0

    def exec_app(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        arguments = ("exec", "-T", *_environment_flags(command), APP_SERVICE, *command.command)
        return self._command(plan, arguments, command)

    def run_one_off(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        arguments = (
            *("run", "--rm", "-T", "--no-deps", *_PULL_NEVER),
            *_environment_flags(command),
            APP_SERVICE,
            *command.command,
        )
        return self._command(plan, arguments, command)

    def _command(
        self, plan: StackPlan, arguments: tuple[str, ...], command: ContainerCommand
    ) -> CommandOutcome:
        result = self._compose(plan, arguments, command.timeout_s, command.on_output)
        return _outcome(result)

    def install(
        self, plan: InstallPlan, timeout_s: float, on_output: Callable[[str], None] | None
    ) -> CommandOutcome:
        _prepare_project(plan.paths)
        run = _run_folder(plan.paths)
        _write_file(run / STACK_FILE, render_compose(install_document(plan)))
        _write_passwd(run, plan.user)
        arguments = ("run", "--rm", "-T", *_PULL_NEVER, INSTALL_SERVICE)
        return _outcome(self._compose(plan, arguments, timeout_s, on_output))


class _ServiceState:
    """One line of `docker compose ps`."""

    __slots__ = ("exit_code", "exited")

    def __init__(self, document: dict[str, object]) -> None:
        self.exited = document.get("State") in ("exited", "dead")
        code = document.get("ExitCode")
        self.exit_code = code if isinstance(code, int) else 0

    @property
    def failed(self) -> bool:
        return self.exited and self.exit_code != 0


def _parsed_states(output: str) -> dict[str, _ServiceState]:
    """Compose prints one JSON object per line, and older versions one array."""
    text = output.strip()
    if not text:
        return {}
    lines = [text] if text.startswith("[") else text.splitlines()
    states: dict[str, _ServiceState] = {}
    for line in lines:
        with suppress(json.JSONDecodeError):
            found: object = json.loads(line)
            for document in cast(list[object], found) if isinstance(found, list) else [found]:
                if isinstance(document, dict):
                    entry = cast(dict[str, object], document)
                    states[str(entry.get("Service"))] = _ServiceState(entry)
    return states


def _service_failure(up: ProbeResult, budget: StartupBudget) -> str:
    if up.exit_code == TIMED_OUT_EXIT_CODE or "not healthy after" in up.output:
        return (
            f"the stack did not become ready within its startup budget of {budget.up_s} s. "
            f"{_NOT_YOUR_CODE} A busy machine can take this long; run the command again."
        )
    return f"the stack did not start: {_tail(up.output).strip()}\n{_NOT_YOUR_CODE}"


def _refused_or_stopped(output: str) -> EngineStatus:
    if _PERMISSION_REFUSED in output.lower():
        return EngineStatus.NO_PERMISSION
    return EngineStatus.STOPPED


def _start_commands(platform: str) -> tuple[tuple[str, ...], ...]:
    desktop = (DOCKER, "desktop", "start", "--detach")
    if platform == MACOS_PLATFORM:
        return (desktop, ("open", "-a", "Docker"))
    return (desktop, ("systemctl", "--user", "start", "docker-desktop"))


def _loopback_port(output: str) -> int | None:
    host, _, port = output.strip().rpartition(":")
    return int(port) if host == LOOPBACK and port.isdigit() and int(port) > 0 else None


def _environment_flags(command: ContainerCommand) -> tuple[str, ...]:
    return tuple(
        flag for name, value in command.environment.items() for flag in ("-e", f"{name}={value}")
    )


def _outcome(result: ProbeResult | None) -> CommandOutcome:
    if result is None:
        return CommandOutcome(1, "docker is not installed")
    return CommandOutcome(
        result.exit_code, result.output, timed_out=result.exit_code == TIMED_OUT_EXIT_CODE
    )


def _tail(text: str) -> str:
    return text[-TAIL_BYTES:]


def _container(line: str) -> StackContainer:
    stack, kind, workspace, owner = _fields(line, 4)
    return StackContainer(stack, kind, workspace, int(owner) if owner.isdigit() else None)


def _resource(line: str) -> StackResource:
    name, stack, kind, workspace = _fields(line, 4)
    return StackResource(name, stack, kind, workspace)


def _fields(line: str, count: int) -> list[str]:
    fields = line.split("\t")
    return fields + [""] * (count - len(fields))


def _prepare_project(paths: SandboxPaths) -> None:
    """The read-only sub-mount needs its folder. Sandboxed code can leave a link there, and a bind
    mount would follow it to wherever it points on your machine, so a link is refused."""
    devcontainer = Path(paths.devcontainer)
    if devcontainer.is_symlink():
        raise SandboxError(
            f"{devcontainer} is a symbolic link, and cstudy does not mount what a link names. "
            "Delete it, then run the command again."
        )
    try:
        devcontainer.mkdir(exist_ok=True)
    except FileExistsError:
        raise SandboxError(f"{devcontainer} is not a directory; move it aside") from None
    clear_setuid_bits(Path(paths.project))


def _run_folder(paths: SandboxPaths) -> Path:
    run = Path(paths.run)
    run.mkdir(parents=True, exist_ok=True)
    return run


def _write_stack_files(plan: StackPlan) -> None:
    run = _run_folder(plan.paths)
    _write_file(run / STACK_FILE, render_compose(stack_document(plan)))
    _write_passwd(run, plan.user)
    forwarder = run / FORWARDER_FILE
    shutil.copyfile(_FORWARDER_SOURCE, forwarder)
    forwarder.chmod(READABLE_FILE)
    if plan.mocks is not None:
        _write_file(run / MOCK_CONFIG_FILE, plan.mocks.rendered_config)
        _copy_mock_code(run / MOCK_CODE_DIRECTORY)


def _write_passwd(run: Path, user: SandboxUser) -> None:
    _write_file(run / PASSWD_FILE, user.passwd_line)


def _write_file(path: Path, text: str) -> None:
    """Readable by the container's user, whatever the umask is here."""
    path.write_text(text, encoding="utf-8")
    path.chmod(READABLE_FILE)


def _copy_mock_code(target: Path) -> None:
    """Always a copy: Docker Desktop refuses a Homebrew prefix, and silently mounts its own VM's
    folder for `/usr/local/bin`."""
    target.mkdir(exist_ok=True)
    target.chmod(READABLE_DIRECTORY)
    if _MOCK_CODE_SOURCE.is_dir():
        shutil.copytree(
            _MOCK_CODE_SOURCE,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__"),
        )


def _remove_folder(folder: Path) -> None:
    """A link is removed, never followed."""
    if folder.is_symlink():
        folder.unlink()
    elif folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)
