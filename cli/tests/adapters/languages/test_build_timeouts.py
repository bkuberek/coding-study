"""A build tool that never finishes is stopped, named, and takes its children with it
(docs/specs/runners.md#build-timeouts). The tools are fake scripts that start a child and wait."""

import os
import stat
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from coding_study.adapters.languages.bounded_process import BoundedProcess
from coding_study.adapters.languages.go.toolchain import SubprocessGo
from coding_study.adapters.languages.jvm.gradle import WrapperGradle
from coding_study.adapters.languages.rust.toolchain import SubprocessCargo
from coding_study.adapters.languages.typescript.runner import PnpmTypeChecker
from coding_study.adapters.process_liveness import is_alive
from coding_study.domain.errors import RunnerStartError
from tests.adapters.languages.jvm.fake_gradle import FixedJdk

LIMIT_SECONDS = 2.0
CHILD_PID_FILE = "child.pid"
HANGING_TOOL = f"#!/bin/sh\nsleep 300 &\necho $! > {CHILD_PID_FILE}\nwait\n"
DEATH_WAIT_SECONDS = 10.0

type HungBuild = Callable[[Path, pytest.MonkeyPatch], Callable[[], object]]


def install_tool(directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    tool = directory / name
    tool.write_text(HANGING_TOOL)
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)


def on_path(directory: Path, name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    install_tool(directory / "bin", name)
    monkeypatch.setenv("PATH", f"{directory / 'bin'}{os.pathsep}{os.environ['PATH']}")


def hung_go(root: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], object]:
    on_path(root, "go", monkeypatch)
    return lambda: SubprocessGo(LIMIT_SECONDS).build([], root, {})


def hung_cargo(root: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], object]:
    on_path(root, "cargo", monkeypatch)
    return lambda: SubprocessCargo(LIMIT_SECONDS).build([], root, {})


def hung_rustc(root: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], object]:
    on_path(root, "rustc", monkeypatch)
    return lambda: SubprocessCargo(LIMIT_SECONDS).host(root)


def hung_gradle(root: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], object]:
    install_tool(root, "gradlew")
    return lambda: WrapperGradle(root, root / "gradle-home", FixedJdk(), LIMIT_SECONDS).run([])


def hung_tsc(root: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], object]:
    on_path(root, "pnpm", monkeypatch)
    return lambda: PnpmTypeChecker(LIMIT_SECONDS).check(root)


HUNG_BUILDS: dict[str, HungBuild] = {
    "go build": hung_go,
    "cargo build": hung_cargo,
    "rustc -vV": hung_rustc,
    "Gradle build": hung_gradle,
    "tsc": hung_tsc,
}


def run_hung(step: str, root: Path, monkeypatch: pytest.MonkeyPatch) -> RunnerStartError:
    build = HUNG_BUILDS[step](root, monkeypatch)
    with pytest.raises(RunnerStartError) as raised:
        build()
    return raised.value


def child_pid(root: Path) -> int:
    return int((root / CHILD_PID_FILE).read_text())


def wait_until_dead(pid: int) -> bool:
    deadline = time.monotonic() + DEATH_WAIT_SECONDS
    while is_alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    return not is_alive(pid)


@pytest.mark.slow
@pytest.mark.parametrize("step", HUNG_BUILDS)
def test_a_hung_build_is_stopped_and_named(step, tmp_path, monkeypatch):
    error = run_hung(step, tmp_path, monkeypatch)
    assert f"{step} did not finish within {LIMIT_SECONDS:g} s and was stopped" in str(error)


@pytest.mark.slow
@pytest.mark.parametrize("step", HUNG_BUILDS)
def test_a_hung_build_leaves_no_process_behind(step, tmp_path, monkeypatch):
    run_hung(step, tmp_path, monkeypatch)
    assert wait_until_dead(child_pid(tmp_path))


@pytest.mark.slow
def test_a_hung_build_shows_what_it_last_wrote(tmp_path):
    tool = tmp_path / "tool"
    tool.write_text(
        "#!/bin/sh\necho 'Blocking waiting for file lock on package cache'\nsleep 300\n"
    )
    tool.chmod(0o755)
    with pytest.raises(RunnerStartError) as raised:
        BoundedProcess("cargo build", LIMIT_SECONDS).run([str(tool)], tmp_path, None)
    assert raised.value.stderr_tail == ("Blocking waiting for file lock on package cache",)


def test_a_finished_tool_returns_both_streams_and_its_exit_code(tmp_path):
    command = ["/bin/sh", "-c", "echo out; echo err >&2; exit 3"]
    completed = BoundedProcess("tool").run(command, tmp_path, None)
    assert (completed.returncode, completed.stdout, completed.stderr) == (3, b"out\n", b"err\n")


def test_interleaved_output_holds_standard_error_in_standard_output(tmp_path):
    command = ["/bin/sh", "-c", "echo out; echo err >&2"]
    completed = BoundedProcess("tool").run_interleaved(command, tmp_path, None)
    assert (completed.stdout, completed.stderr) == (b"out\nerr\n", b"")


def test_a_tool_that_cannot_start_raises_the_operating_system_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        BoundedProcess("tool").run(["/nonexistent/tool"], tmp_path, None)
