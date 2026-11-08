"""`SandboxEngine` over the Docker command line (docs/specs/service-projects.md#sandbox).

Every call runs with standard input at end of file, and never with `-y`: a label that changes on a
volume makes compose ask whether to recreate it, which hangs on an open pipe and loses the data
under `-y`. Readiness is `docker info`, which starts nothing and wakes no idle VM, never `docker
desktop status`, which said `stopped` while the engine answered, and never `docker system df`,
which wakes the VM.
"""

import codecs
import http.client
import io
import ipaddress
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Generator, Iterable, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import IO, Protocol, cast

from coding_study.adapters.docker_setup import docker_group_of_this_process, engine_setup
from coding_study.adapters.http_grader.clients import DeadlineConnection
from coding_study.adapters.process_environment import docker_environment
from coding_study.adapters.process_liveness import is_alive
from coding_study.adapters.project_folders import clear_setuid_bits
from coding_study.adapters.stack_guard import DOCKER, DOCKER_FOLDER, StackGuard, one_off_filters
from coding_study.application.ports import ContainerCommand, ProbeResult, ProgressNotice
from coding_study.domain.docker_engine import (
    MACOS_PLATFORM,
    ROOTLESS_ENGINE_START,
    DockerGroup,
    EngineSetup,
    EngineState,
    EngineStatus,
    did_not_start_message,
)
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    APP_SERVICE,
    BOOTSTRAP_SERVICE,
    CONTROL_PORT,
    EGRESS_HOSTS_VARIABLE,
    EGRESS_PROBE_SERVICE,
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
    RESET_PREPARE_SERVICE,
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
    is_stack_name,
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
MAX_OUTPUT_BYTES = 1024 * 1024
"""How much of a command's output a result holds: its end, far past what any report shows."""
MAX_LINE_CHARACTERS = 64 * 1024
"""The most a listener hears at once: a longer line comes in pieces, or one with no newline at all
would grow without limit."""
_READ_CHUNK_BYTES = 64 * 1024
LOOPBACK = "127.0.0.1"
HTTP_OK_FIRST = 200
HTTP_OK_LAST = 299
READABLE_FILE = 0o644
READABLE_DIRECTORY = 0o755
MILLISECONDS_PER_SECOND = 1000
EGRESS_PROBE_LIMIT_S = 60.0
IPV4 = 4
_GATEWAY_FORMAT = "{{range .IPAM.Config}}{{.Gateway}} {{end}}"
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
_ENGINE_VERSION = re.compile(r"\d+\.\d+(\.\d+)?([-+~][0-9A-Za-z.+~-]*)?")
"""What `docker info` prints for an engine that answers, such as `29.8.1` or `20.10.24+dfsg1`. The
Docker 28.0 client exits 0 when no engine answers, with its error as the only output."""
_ENDING_SIGNALS = (signal.SIGINT, signal.SIGTERM)
_START_THE_APP_ALONE = (
    *("up", "--detach", "--no-deps", "--no-recreate", "--no-build", *_PULL_NEVER),
    APP_SERVICE,
)
"""`docker compose start app` runs the one-shots it depends on again, `bootstrap` among them, on
data a case has already changed."""

type HealthProbe = Callable[[int, str], bool]


class DockerRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        timeout_s: float | None = None,
        on_line: Callable[[str], None] | None = None,
    ) -> ProbeResult | None:
        """Runs a command to its end with standard input at end of file; None when the executable
        is missing, and `TIMED_OUT_EXIT_CODE` when `timeout_s` ran out, with the process killed.
        The result holds the end of the output, up to `MAX_OUTPUT_BYTES`, however much went by."""
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
                env=docker_environment(),
                start_new_session=True,
                cwd=DOCKER_FOLDER,
            )
        except FileNotFoundError:
            return None
        except OSError as error:
            return ProbeResult(NOT_EXECUTABLE_EXIT_CODE, str(error))
        return _finished(process, timeout_s, on_line)


def _finished(
    process: subprocess.Popen[bytes],
    timeout_s: float | None,
    on_line: Callable[[str], None] | None,
) -> ProbeResult:
    output = _BoundedOutput(on_line)
    assert process.stdout is not None
    reader = threading.Thread(target=_collect, args=(process.stdout, output), daemon=True)
    reader.start()
    try:
        process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _kill_group(process)
        reader.join(READ_GRACE_S)
        return ProbeResult(TIMED_OUT_EXIT_CODE, output.text())
    except BaseException:
        _kill_group(process)
        raise
    reader.join(READ_GRACE_S)
    return ProbeResult(process.returncode, output.text())


def _collect(stream: IO[bytes], output: "_BoundedOutput") -> None:
    while chunk := os.read(stream.fileno(), _READ_CHUNK_BYTES):
        output.take(chunk)
    output.finish()


class _BoundedOutput:
    """What a container prints is as long as it likes, and `cstudy dev` follows an app with no limit
    on time. So this holds the output's end and one unfinished line, and each line goes by."""

    def __init__(self, on_line: Callable[[str], None] | None) -> None:
        self._end = bytearray()
        self._on_line = on_line
        self._unfinished = ""
        self._decoder = _text_decoder()

    def take(self, chunk: bytes) -> None:
        self._end += chunk
        del self._end[:-MAX_OUTPUT_BYTES]
        if self._on_line is not None:
            self._hear(self._decoder.decode(chunk))

    def finish(self) -> None:
        if self._on_line is not None:
            self._hear(self._decoder.decode(b"", final=True))
            self._say(_pieces(self._unfinished) if self._unfinished else ())
            self._unfinished = ""

    def text(self) -> str:
        return _text_decoder().decode(bytes(self._end), final=True)

    def _hear(self, text: str) -> None:
        *lines, unfinished = (self._unfinished + text).split("\n")
        for line in lines:
            self._say(_pieces(line))
        *whole, self._unfinished = _pieces(unfinished)
        self._say(whole)

    def _say(self, pieces: Iterable[str]) -> None:
        assert self._on_line is not None
        for piece in pieces:
            self._on_line(piece)


def _text_decoder() -> io.IncrementalNewlineDecoder:
    """UTF-8 whatever comes, and every line ending as `\\n`, across any split between two reads."""
    return io.IncrementalNewlineDecoder(
        codecs.getincrementaldecoder("utf-8")("replace"), translate=True
    )


def _pieces(line: str) -> list[str]:
    """`line` cut to `MAX_LINE_CHARACTERS`; an empty line is one empty piece."""
    size = MAX_LINE_CHARACTERS
    return [line[start : start + size] for start in range(0, len(line), size)] or [""]


def _kill_group(process: subprocess.Popen[bytes]) -> None:
    with suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def default_docker_runner() -> DockerRunner:
    """What `DockerSandbox` runs commands with; the tests replace this one function, so that no
    fast test ever reaches a real engine."""
    return SubprocessDockerRunner()


def http_health(port: int, path: str) -> bool:
    """Asks `127.0.0.1` directly: no proxy from the environment, and no redirect followed. The
    limit is on the whole exchange: this is your app talking, and it can send a byte now and then,
    or `100 Continue` for ever, and `start` must still get to read the app's state."""
    connection = DeadlineConnection((LOOPBACK, port), HEALTH_PROBE_TIMEOUT_S)
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
        docker_group: Callable[[], DockerGroup] = docker_group_of_this_process,
    ) -> None:
        self._runner = runner or default_docker_runner()
        self._runs_directory = runs_directory
        self._health_probe = health_probe
        self._monotonic = monotonic
        self._sleep = sleep
        self._platform = platform
        self._docker_group = docker_group

    def state(self) -> EngineState:
        info = self._runner.run((DOCKER, "info", "--format", "{{.ServerVersion}}"), ENGINE_QUERY_S)
        if info is None:
            return EngineState(EngineStatus.NOT_INSTALLED)
        version = info.output.strip()
        if not _answers(info):
            status = _refused_or_stopped(info.output)
            if status is EngineStatus.NO_PERMISSION:
                return EngineState(status, docker_group=self._docker_group())
            return EngineState(status)
        compose = self._runner.run((DOCKER, "compose", "version", "--short"), ENGINE_QUERY_S)
        if compose is None or compose.exit_code != 0:
            return EngineState(EngineStatus.NO_COMPOSE, version)
        return EngineState(EngineStatus.RUNNING, version, compose.output.strip())

    def platform(self) -> str:
        return self._platform

    def host_user(self) -> SandboxUser:
        return SandboxUser(os.getuid(), os.getgid())

    def owner_pid(self) -> int:
        return os.getpid()

    def start_engine(self, notify: ProgressNotice) -> None:
        notify("starting Docker ...")
        setup = self._setup()
        for command in _start_commands(self._platform, setup):
            started = self._runner.run(command, ENGINE_QUERY_S)
            if started is not None and started.exit_code == 0:
                self._wait_for_engine()
                return
        raise SandboxError(did_not_start_message(setup))

    def _setup(self) -> EngineSetup:
        if self._platform == MACOS_PLATFORM:
            return EngineSetup.OTHER
        return engine_setup(self._runner, os.getuid(), os.environ.get("XDG_RUNTIME_DIR"))

    def _wait_for_engine(self) -> None:
        deadline = self._monotonic() + ENGINE_START_S
        while self._monotonic() < deadline:
            info = self._runner.run(
                (DOCKER, "info", "--format", "{{.ServerVersion}}"), ENGINE_QUERY_S
            )
            if info is not None and _answers(info):
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
        if not is_stack_name(stack.name):
            return False
        removed = self._down(stack.name, stack.removes_volumes)
        if removed and self._runs_directory is not None:
            _remove_run_folder(self._runs_directory, stack.name)
        return removed

    def remove_network(self, name: str) -> bool:
        return is_stack_name(name) and self._succeeded((DOCKER, "network", "rm", name))

    def remove_volume(self, name: str) -> bool:
        return is_stack_name(name) and self._succeeded((DOCKER, "volume", "rm", name))

    def _succeeded(self, command: tuple[str, ...]) -> bool:
        result = self._runner.run(command, INVENTORY_TIMEOUT_S)
        return result is not None and result.exit_code == 0

    @contextmanager
    def guard(self, identity: StackIdentity) -> Generator[None]:
        runs = self._runs_directory
        with StackGuard(
            identity.name,
            removes_volumes=identity.kind.removes_volumes,
            environment=docker_environment(),
            run_directory=None if runs is None else runs / identity.name,
        ):
            yield

    def start(self, plan: StackPlan, budget: StartupBudget) -> ReadyStack:
        started_at = self._monotonic()
        _prepare_project(plan.paths)
        if plan.grade_setup is not None:
            _refuse_link(Path(plan.grade_setup.grading_directory))
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
            self._app_output(plan),
        )

    def _app_output(self, plan: StackPlan) -> str:
        """The app's last lines, after what the engine knows and they cannot say."""
        logs = self._logs(plan, APP_SERVICE)
        if not self._ran_out_of_memory(plan):
            return logs
        return f"the container hit its memory limit of {plan.app.mem_limit}\n{logs}"

    def _app_container(self, plan: StackPlan) -> str:
        listed = self._compose(plan, ("ps", "-a", "-q", APP_SERVICE), ENGINE_QUERY_S)
        return listed.output.strip() if listed is not None else ""

    def _ran_out_of_memory(self, plan: StackPlan) -> bool:
        container = self._app_container(plan)
        if not container:
            return False
        state = self._runner.run(
            (DOCKER, "inspect", "--format", "{{.State.OOMKilled}}", container), ENGINE_QUERY_S
        )
        return state is not None and state.output.strip() == "true"

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
        for service, name in ((BOOTSTRAP_SERVICE, "bootstrap"), (RESET_PREPARE_SERVICE, "reset")):
            if (one_shot := states.get(service)) and one_shot.failed:
                return StackStartError(
                    StartupFailure.BOOTSTRAP,
                    f"{name} exited with code {one_shot.exit_code}",
                    self._logs(plan, service),
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
        with _signals_held_off():
            down = self._down(identity.name, identity.kind.removes_volumes)
        clear_setuid_bits(Path(paths.project))
        if not down:
            return f"could not take {identity.name} down; the next run or doctor --fix will"
        _remove_folder(Path(paths.run))
        return None

    def _down(self, name: str, removes_volumes: bool) -> bool:
        self._remove_one_offs(name)
        flags = ("-v",) if removes_volumes else ()
        down = self._runner.run((*_COMPOSE, "-p", name, "down", *flags), STOP_TIMEOUT_S)
        return down is not None and down.exit_code == 0

    def _remove_one_offs(self, stack: str) -> None:
        found = self._runner.run(
            (DOCKER, "ps", "-aq", *one_off_filters(stack)), INVENTORY_TIMEOUT_S
        )
        one_offs = found.output.split() if found is not None and found.exit_code == 0 else []
        if one_offs:
            self._runner.run((DOCKER, "rm", "-f", "-v", *one_offs), STOP_TIMEOUT_S)

    def exec_app(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        arguments = ("exec", "-T", *_environment_flags(command), APP_SERVICE, *command.command)
        return _outcome(self._compose(plan, arguments, command.timeout_s, command.on_output))

    def run_one_off(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        arguments = (
            *("run", "--rm", "-T", "--no-deps", *_PULL_NEVER),
            *_environment_flags(command),
            APP_SERVICE,
            *command.command,
        )
        return self._one_off(plan, arguments, command.timeout_s, command.on_output)

    def _one_off(
        self,
        plan: StackPlan | InstallPlan,
        arguments: tuple[str, ...],
        timeout_s: float,
        on_output: Callable[[str], None] | None = None,
    ) -> CommandOutcome:
        """`docker compose run`. Past its limit the client is killed and the container runs on
        without it, on the data of whatever comes next, so it goes at once."""
        outcome = _outcome(self._compose(plan, arguments, timeout_s, on_output))
        if outcome.timed_out:
            self._remove_one_offs(plan.identity.name)
        return outcome

    def restart_app(self, plan: StackPlan, ready: ReadyStack, budget: StartupBudget) -> None:
        self.stop_app(plan)
        self.start_app(plan, ready, budget)

    def stop_app(self, plan: StackPlan) -> None:
        stopped = self._compose(plan, ("stop", APP_SERVICE), STOP_TIMEOUT_S)
        if stopped is None or stopped.exit_code != 0:
            output = stopped.output.strip() if stopped is not None else "docker is not installed"
            raise StackStartError(
                StartupFailure.SERVICE, f"could not stop the app: {output}. {_NOT_YOUR_CODE}"
            )

    def start_app(self, plan: StackPlan, ready: ReadyStack, budget: StartupBudget) -> None:
        started = self._compose(plan, _START_THE_APP_ALONE, budget.up_s)
        if started is None or started.exit_code != 0:
            output = started.output.strip() if started is not None else "docker is not installed"
            raise StackStartError(
                StartupFailure.SERVICE, f"could not start the app: {output}. {_NOT_YOUR_CODE}"
            )
        self._wait_for_health(plan, ready.app_port, budget)

    def app_exit(self, plan: StackPlan, within_ms: int) -> CommandOutcome | None:
        deadline = self._monotonic() + within_ms / MILLISECONDS_PER_SECOND
        while True:
            state = self._service_states(plan).get(APP_SERVICE)
            if state is not None and state.exited:
                return CommandOutcome(state.exit_code, self._app_output(plan))
            if self._monotonic() >= deadline:
                return None
            self._sleep(HEALTH_POLL_S)

    def follow_app(self, plan: StackPlan, on_line: Callable[[str], None]) -> None:
        """`docker logs`, since `docker compose logs --follow` keeps waiting after its container
        ended."""
        container = self._app_container(plan)
        if container:
            self._runner.run((DOCKER, "logs", "--follow", container), None, on_line)

    def probe_egress(self, plan: StackPlan) -> CommandOutcome:
        hosts = ",".join(sorted(self._gateways(plan), key=ipaddress.IPv4Address))
        arguments = (
            *("run", "--rm", "-T", "--no-deps", *_PULL_NEVER),
            *("-e", f"{EGRESS_HOSTS_VARIABLE}={hosts}"),
            EGRESS_PROBE_SERVICE,
        )
        return self._one_off(plan, arguments, EGRESS_PROBE_LIMIT_S)

    def _gateways(self, plan: StackPlan) -> set[str]:
        """The IPv4 gateway of each of the stack's networks: where a bridge holds one, it is an
        address of this machine's."""
        project = f"label={LABEL_PROJECT}={plan.identity.name}"
        listed = self._runner.run(
            (DOCKER, "network", "ls", "-q", "--filter", project), INVENTORY_TIMEOUT_S
        )
        networks = listed.output.split() if listed is not None and listed.exit_code == 0 else []
        if not networks:
            return set()
        found = self._runner.run(
            (DOCKER, "network", "inspect", "--format", _GATEWAY_FORMAT, *networks),
            INVENTORY_TIMEOUT_S,
        )
        words = found.output.split() if found is not None and found.exit_code == 0 else []
        return {word for word in words if _is_ipv4(word)}

    def install(
        self, plan: InstallPlan, timeout_s: float, on_output: Callable[[str], None] | None
    ) -> CommandOutcome:
        _prepare_project(plan.paths)
        run = _run_folder(plan.paths)
        _write_file(run / STACK_FILE, render_compose(install_document(plan)))
        _write_passwd(run, plan.user)
        arguments = ("run", "--rm", "-T", *_PULL_NEVER, INSTALL_SERVICE)
        return self._one_off(plan, arguments, timeout_s, on_output)


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


@contextmanager
def _signals_held_off() -> Generator[None]:
    """A second Ctrl-C during `down` would leave half a stack behind. Off the main thread, where no
    handler can be set, signals never arrive anyway."""
    try:
        held = {number: signal.signal(number, signal.SIG_IGN) for number in _ENDING_SIGNALS}
    except ValueError:
        yield
        return
    try:
        yield
    finally:
        for number, previous in held.items():
            signal.signal(number, previous)


def _service_failure(up: ProbeResult, budget: StartupBudget) -> str:
    if up.exit_code == TIMED_OUT_EXIT_CODE or "not healthy after" in up.output:
        return (
            f"the stack did not become ready within its startup budget of {budget.up_s} s. "
            f"{_NOT_YOUR_CODE} A busy machine can take this long; run the command again."
        )
    return f"the stack did not start: {_tail(up.output).strip()}\n{_NOT_YOUR_CODE}"


def _answers(info: ProbeResult) -> bool:
    """Whether an engine answered `docker info`: the Docker 28.0 client exits 0 with only its error
    when none does, so the exit code alone does not say."""
    return info.exit_code == 0 and _ENGINE_VERSION.fullmatch(info.output.strip()) is not None


def _refused_or_stopped(output: str) -> EngineStatus:
    if _PERMISSION_REFUSED in output.lower():
        return EngineStatus.NO_PERMISSION
    return EngineStatus.STOPPED


def _start_commands(platform: str, setup: EngineSetup) -> tuple[tuple[str, ...], ...]:
    """Only what needs no root: Docker Desktop, and the user services of Desktop and rootless
    Docker. Rootless Docker answers at its own address, so Desktop is never started for it."""
    desktop = (DOCKER, "desktop", "start", "--detach")
    if platform == MACOS_PLATFORM:
        return (desktop, ("open", "-a", "Docker"))
    if setup is EngineSetup.ROOTLESS:
        return (tuple(ROOTLESS_ENGINE_START.split()),)
    return (desktop, ("systemctl", "--user", "start", "docker-desktop"))


def _is_ipv4(text: str) -> bool:
    """A bridge with no address shows its gateway as `invalid IP`."""
    try:
        return ipaddress.ip_address(text).version == IPV4
    except ValueError:
        return False


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
    """The read-only sub-mount needs its folder, and a link there is refused."""
    devcontainer = Path(paths.devcontainer)
    _refuse_link(devcontainer)
    try:
        devcontainer.mkdir(exist_ok=True)
    except FileExistsError:
        raise SandboxError(f"{devcontainer} is not a directory; move it aside") from None
    clear_setuid_bits(Path(paths.project))


def _refuse_link(mounted: Path) -> None:
    """A bind mount follows a link to wherever it points on your machine, and sandboxed code can
    leave one in a project folder."""
    if mounted.is_symlink():
        raise SandboxError(
            f"{mounted} is a symbolic link, and cstudy does not mount what a link names. "
            "Delete it, then run the command again."
        )


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
        for found in target.rglob("*"):
            found.chmod(READABLE_DIRECTORY if found.is_dir() else READABLE_FILE)


def _remove_run_folder(runs: Path, name: str) -> None:
    """The folder of a stack named by a label, which must lie directly under `runs`."""
    folder = runs / name
    if folder.parent.resolve().is_relative_to(runs.resolve()):
        _remove_folder(folder)


def _remove_folder(folder: Path) -> None:
    """A link is removed, never followed."""
    if folder.is_symlink():
        folder.unlink()
    elif folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)
