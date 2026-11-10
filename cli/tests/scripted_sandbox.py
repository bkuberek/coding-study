"""A fake Docker for a real `cstudy serve` and the `cstudy` children it starts, for the browser
tests of service projects: `fake_sandbox_site/sitecustomize.py` puts `ScriptedSandbox` in place of
`DockerSandbox` in every process whose environment names a script folder in `SANDBOX_VARIABLE`.

The folder holds `script.json`, read at each step so a test can change it between runs, and
`calls.log`, where each process appends what it was asked, one line each, so a test can say that a
cancelled run's stack came down. Nothing here reaches Docker.
"""

import json
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coding_study.application.ports import ContainerCommand, ProgressNotice
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.sandbox import (
    CommandOutcome,
    InstallPlan,
    ReadyStack,
    StackPlan,
    StartupBudget,
)
from tests.sandbox_fakes import RUNNING, FakeSandbox

SANDBOX_VARIABLE = "CSTUDY_TEST_SANDBOX"
SITE_DIRECTORY = Path(__file__).parent / "fake_sandbox_site"
SCRIPT_FILE = "script.json"
CALLS_FILE = "calls.log"
CLI_DIRECTORY = Path(__file__).parents[1]
DEFAULT_TEST_LINES = ("ok 1 - rooms",)


def sandbox_variables(folder: Path, script: Mapping[str, object]) -> dict[str, str]:
    """What a served `cstudy` needs in its environment to use the fake, with `script` written."""
    folder.mkdir(parents=True, exist_ok=True)
    write_script(folder, script)
    path = os.pathsep.join([str(SITE_DIRECTORY), str(CLI_DIRECTORY)])
    return {SANDBOX_VARIABLE: str(folder), "PYTHONPATH": path}


def write_script(folder: Path, script: Mapping[str, object]) -> None:
    """`engine` (an `EngineStatus` value), `start_s`, `test_s` (how long the stack takes to start
    and `commands.test` to run), `test_exit` and `test_lines`."""
    (folder / SCRIPT_FILE).write_text(json.dumps(script))


@dataclass(frozen=True, slots=True)
class SandboxScript:
    engine: str = RUNNING.status.value
    start_s: float = 0.0
    test_s: float = 0.0
    test_exit: int = 0
    test_lines: tuple[str, ...] = DEFAULT_TEST_LINES

    @classmethod
    def read(cls, folder: Path) -> "SandboxScript":
        document: dict[str, Any] = json.loads((folder / SCRIPT_FILE).read_text())
        lines = tuple(str(line) for line in document.pop("test_lines", DEFAULT_TEST_LINES))
        return cls(**document, test_lines=lines)


def logged_calls(folder: Path) -> list[str]:
    path = folder / CALLS_FILE
    return path.read_text().splitlines() if path.exists() else []


class ScriptedSandbox(FakeSandbox):
    """`DockerSandbox(runs_directory=...)`'s stand-in."""

    def __init__(self, runs_directory: Path | None = None) -> None:
        super().__init__()
        self._folder = Path(os.environ[SANDBOX_VARIABLE])

    def state(self) -> EngineState:
        status = EngineStatus(self._script().engine)
        return RUNNING if status is EngineStatus.RUNNING else EngineState(status)

    def start(self, plan: StackPlan, budget: StartupBudget) -> ReadyStack:
        self._log(f"start {plan.identity.name}")
        began = time.monotonic()
        time.sleep(self._script().start_s)
        return ReadyStack(plan.identity.name, self.app_port, None, began, time.monotonic())

    def stop(self, plan: StackPlan) -> str | None:
        self._log(f"stop {plan.identity.name}")
        return None

    def exec_app(self, plan: StackPlan, command: ContainerCommand) -> CommandOutcome:
        script = self._script()
        for line in script.test_lines:
            if command.on_output is not None:
                command.on_output(line)
        time.sleep(script.test_s)
        return CommandOutcome(script.test_exit, "\n".join(script.test_lines) + "\n")

    def install(
        self, plan: InstallPlan, timeout_s: float, on_output: Callable[[str], None] | None
    ) -> CommandOutcome:
        self._log("install")
        return CommandOutcome(0, "installed\n")

    def pull(self, image: str, notify: ProgressNotice) -> None:
        self._log(f"pull {image}")

    def _script(self) -> SandboxScript:
        return SandboxScript.read(self._folder)

    def _log(self, line: str) -> None:
        with (self._folder / CALLS_FILE).open("a") as calls:
            calls.write(f"{line}\n")
