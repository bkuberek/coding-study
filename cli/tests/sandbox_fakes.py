"""A `SandboxEngine` that records what the application asks of it, and a Docker runner that answers
as scripted, so nothing but the slow tests reaches a real engine."""

from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field

from coding_study.application.ports import (
    ContainerCommand,
    ProbeResult,
    ProgressNotice,
)
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    CommandOutcome,
    InstallPlan,
    LeftoverStack,
    ReadyStack,
    SandboxInventory,
    SandboxUser,
    ServiceChange,
    SidecarPlan,
    StackIdentity,
    StackPlan,
    StackStartError,
    StartupBudget,
)

RUNNING = EngineState(EngineStatus.RUNNING, "29.9.2", "5.6.1")


@dataclass
class FakeSandbox:
    """Calls are logged as `(name, detail)` in order."""

    engine: EngineState = RUNNING
    platform_name: str = "darwin"
    present: set[str] = field(default_factory=set[str])
    every_image_present: bool = True
    inventory_found: SandboxInventory = field(default_factory=SandboxInventory)
    live_pids: set[int] = field(default_factory=set[int])
    removes_stacks: bool = True
    calls: list[tuple[str, object]] = field(default_factory=list[tuple[str, object]])
    start_error: StackStartError | None = None
    started_engine_state: EngineState = RUNNING
    exec_outcome: CommandOutcome = field(default_factory=lambda: CommandOutcome(0, "ok\n"))
    install_outcome: CommandOutcome = field(default_factory=lambda: CommandOutcome(0, "ok\n"))
    ready_at: float = 12.5
    started_at: float = 10.0
    app_port: int = 56223
    control_port: int | None = None
    debug_port: int = 50229
    """Where a plan's published debug port lands, when it has one."""
    pull_error: Exception | None = None
    plans: list[StackPlan] = field(default_factory=list[StackPlan])
    after_install: Callable[[], None] | None = None
    install_timeouts: list[float] = field(default_factory=list[float])
    one_off_outcome: CommandOutcome = field(default_factory=lambda: CommandOutcome(0, "ok\n"))
    start_app_error: StackStartError | None = None
    service_error: StackStartError | None = None
    app_ended: CommandOutcome | None = None
    app_lines: tuple[str, ...] = ()
    probe_outcome: CommandOutcome = field(default_factory=lambda: CommandOutcome(0, "reached []\n"))
    on_follow: Callable[[], None] | None = None
    """What happens while `follow_app` would block: a test raises KeyboardInterrupt here."""
    app_output: str = ""
    app_output_error: SandboxError | None = None
    sidecar_error: SandboxError | None = None

    def state(self) -> EngineState:
        self.calls.append(("state", None))
        return self.engine

    def platform(self) -> str:
        return self.platform_name

    def host_user(self) -> SandboxUser:
        return SandboxUser(501, 20)

    def owner_pid(self) -> int:
        return 41

    def start_engine(self, notify: ProgressNotice) -> None:
        self.calls.append(("start_engine", None))
        notify("starting Docker ...")
        self.engine = self.started_engine_state

    def image_present(self, image: str) -> bool:
        return self.every_image_present or image in self.present

    def pull(self, image: str, notify: ProgressNotice) -> None:
        self.calls.append(("pull", image))
        if self.pull_error is not None:
            raise self.pull_error
        notify(f"pulled {image}")
        self.present.add(image)

    def inventory(self) -> SandboxInventory:
        self.calls.append(("inventory", None))
        return self.inventory_found

    def is_alive(self, pid: int) -> bool:
        return pid in self.live_pids

    def remove_stack(self, stack: LeftoverStack) -> bool:
        self.calls.append(("remove_stack", stack))
        return self.removes_stacks

    def remove_network(self, name: str) -> bool:
        self.calls.append(("remove_network", name))
        return True

    def remove_volume(self, name: str) -> bool:
        self.calls.append(("remove_volume", name))
        return True

    @contextmanager
    def guard(self, identity: StackIdentity) -> Generator[None]:
        self.calls.append(("guard", identity.name))
        try:
            yield
        finally:
            self.calls.append(("guard_released", identity.name))

    def start(self, plan: StackPlan, budget: StartupBudget) -> ReadyStack:
        self.calls.append(("start", budget))
        self.plans.append(plan)
        if self.start_error is not None:
            raise self.start_error
        debug = self.debug_port if plan.published_debug_port is not None else None
        return ReadyStack(
            plan.identity.name,
            self.app_port,
            self.control_port,
            self.started_at,
            self.ready_at,
            debug_port=debug,
        )

    def stop(self, plan: StackPlan) -> str | None:
        self.calls.append(("stop", plan.identity.name))
        return None

    def exec_app(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        self.calls.append(("exec_app", command))
        if command.on_output is not None:
            for line in self.exec_outcome.output.splitlines():
                command.on_output(line)
        return self.exec_outcome

    def run_one_off(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        self.calls.append(("run_one_off", command))
        return self.one_off_outcome

    def restart_app(self, plan: StackPlan, ready: ReadyStack, budget: StartupBudget) -> None:
        self.calls.append(("restart_app", budget))
        if self.start_app_error is not None:
            raise self.start_app_error

    def stop_app(self, plan: StackPlan) -> None:
        self.calls.append(("stop_app", plan.identity.name))

    def start_app(self, plan: StackPlan, ready: ReadyStack, budget: StartupBudget) -> None:
        self.calls.append(("start_app", budget))
        if self.start_app_error is not None:
            raise self.start_app_error

    def change_service(self, plan: StackPlan, change: ServiceChange, budget: StartupBudget) -> None:
        self.calls.append(("change_service", (change, budget)))
        if self.service_error is not None:
            raise self.service_error

    def app_exit(self, plan: StackPlan, within_ms: int) -> CommandOutcome | None:
        self.calls.append(("app_exit", within_ms))
        return self.app_ended

    def app_output_since(self, plan: StackPlan, since_s: float) -> str:
        self.calls.append(("app_output_since", since_s))
        if self.app_output_error is not None:
            raise self.app_output_error
        return self.app_output

    def follow_app(self, plan: StackPlan, on_line: Callable[[str], None]) -> None:
        self.calls.append(("follow_app", plan.identity.name))
        for line in self.app_lines:
            on_line(line)
        if self.on_follow is not None:
            self.on_follow()

    def probe_egress(self, plan: StackPlan) -> CommandOutcome:
        self.calls.append(("probe_egress", plan.identity.name))
        return self.probe_outcome

    def install(
        self, plan: InstallPlan, timeout_s: float, on_output: Callable[[str], None] | None
    ) -> CommandOutcome:
        self.calls.append(("install", plan))
        self.install_timeouts.append(timeout_s)
        if self.after_install is not None:
            self.after_install()
        return self.install_outcome

    def stop_install(self, plan: InstallPlan) -> str | None:
        self.calls.append(("stop_install", plan.identity.name))
        return None

    @contextmanager
    def sidecar(self, plan: SidecarPlan) -> Generator[None]:
        """Logs `sidecar` as it comes up and `sidecar_down` once it is gone, with its name."""
        self.calls.append(("sidecar", plan.identity.name))
        try:
            if self.sidecar_error is not None:
                raise self.sidecar_error
            yield
        finally:
            self.calls.append(("sidecar_down", plan.identity.name))

    def sidecar_command(self, plan: SidecarPlan, command: Sequence[str]) -> tuple[str, ...]:
        """The command itself, which then runs on this machine, as a test's fake server does."""
        self.calls.append(("sidecar_command", tuple(command)))
        return tuple(command)

    def called(self, name: str) -> list[object]:
        return [detail for called, detail in self.calls if called == name]


@dataclass
class ScriptedDocker:
    """A Docker runner: answers each command with the first answer whose prefix matches, exit 0
    with no output when none does. `missing` answers everything with None, as a missing binary."""

    answers: list[tuple[tuple[str, ...], ProbeResult | None]] = field(
        default_factory=list[tuple[tuple[str, ...], ProbeResult | None]]
    )
    missing: bool = False
    commands: list[tuple[str, ...]] = field(default_factory=list[tuple[str, ...]])
    timeouts: list[float | None] = field(default_factory=list[float | None])
    streamed: list[str] = field(default_factory=list[str])

    def answer(self, prefix: tuple[str, ...], result: ProbeResult | None) -> None:
        self.answers.append((prefix, result))

    def run(
        self,
        command: Sequence[str],
        timeout_s: float | None = None,
        on_line: Callable[[str], None] | None = None,
    ) -> ProbeResult | None:
        call = tuple(command)
        self.commands.append(call)
        self.timeouts.append(timeout_s)
        if self.missing:
            return None
        for index, (prefix, result) in enumerate(self.answers):
            if _holds(call, prefix):
                del self.answers[index]
                if result is not None and on_line is not None:
                    for line in result.output.splitlines():
                        on_line(line)
                return result
        return ProbeResult(0, "")

    def ran(self, *words: str) -> list[tuple[str, ...]]:
        """The commands that hold `words` next to each other."""
        return [command for command in self.commands if _holds(command, words)]


class DockerMissing:
    """What a Docker runner answers on a machine without Docker."""

    def run(
        self,
        command: Sequence[str],
        timeout_s: float | None = None,
        on_line: Callable[[str], None] | None = None,
    ) -> ProbeResult | None:
        return None


def _holds(command: tuple[str, ...], words: tuple[str, ...]) -> bool:
    size = len(words)
    return any(command[start : start + size] == words for start in range(len(command) - size + 1))
