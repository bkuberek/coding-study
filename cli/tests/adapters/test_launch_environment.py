"""Every launch of user code or a tool on it hands the process the allowlisted environment
(docs/specs/runners.md#process-environment): a secret the shell holds is not among its variables,
and PATH and HOME are, wherever the launch adds nothing of its own and wherever it does."""

import os
import sys
from pathlib import Path

import pytest

from coding_study.adapters.languages.go.toolchain import SubprocessGo
from coding_study.adapters.languages.jvm.gradle import WrapperGradle
from coding_study.adapters.languages.rust.project_suite import SubprocessTests
from coding_study.adapters.languages.rust.toolchain import SubprocessCargo
from coding_study.adapters.languages.typescript.runner import PnpmTypeChecker
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.adapters.subprocess_tool_probe import SubprocessCommandRunner, SubprocessToolProbe
from coding_study.application.ports import RunnerLaunch, RunRequest
from coding_study.domain.errors import RunnerStartError
from tests.adapters.languages.jvm.fake_gradle import FixedJdk
from tests.launch_environment import (
    environment_recorder,
    leaked_secrets,
    missing_needs,
    plant_secrets,
    recorded,
    recording_tool,
)

LAUNCH_VARIABLES = ({}, {"UV_NO_SYNC": "1"})
"""What a launch adds: nothing, as the TypeScript runner's launch, or something."""
PRINT_ENVIRONMENT = (sys.executable, "-I", "-c", "import os; print(*os.environ)")
TEST_LIMIT_MS = 5_000


@pytest.fixture(autouse=True)
def secrets_in_the_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    plant_secrets(monkeypatch)


@pytest.fixture
def record(tmp_path: Path) -> Path:
    return tmp_path / "environment.txt"


def stand_in(tool: str, record: Path, directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Puts a `tool` that records its environment first on PATH."""
    recording_tool(directory / "bin", tool, record)
    monkeypatch.setenv("PATH", f"{directory / 'bin'}{os.pathsep}{os.environ['PATH']}")


def started_environment(record: Path) -> tuple[set[str], set[str]]:
    """The secrets the tool saw, and the needs it did not see."""
    inherited = recorded(record)
    return leaked_secrets(inherited), missing_needs(inherited)


def run_recording_runner(record: Path, tmp_path: Path, variables: dict[str, str]) -> None:
    script = tmp_path / "record_environment.py"
    script.write_text(environment_recorder(record) + "raise SystemExit(1)\n")
    launch = RunnerLaunch((sys.executable, str(script)), tmp_path, 5_000, environment=variables)
    with pytest.raises(RunnerStartError):
        SubprocessRunner(tmp_path / "runs").run(launch, RunRequest(()))


@pytest.mark.parametrize("variables", LAUNCH_VARIABLES)
def test_a_runner_does_not_inherit_a_secret(variables, record, tmp_path):
    run_recording_runner(record, tmp_path, variables)
    assert started_environment(record) == (set(), set())


def test_a_runner_still_gets_the_variables_its_launch_sets(record, tmp_path):
    run_recording_runner(record, tmp_path, {"CARGO_TARGET_DIR": "/t"})
    assert recorded(record)["CARGO_TARGET_DIR"] == "/t"


def test_a_probe_does_not_inherit_a_secret():
    result = SubprocessToolProbe().run(PRINT_ENVIRONMENT)
    assert result is not None
    assert leaked_secrets(result.output.split()) == set()


def test_a_setup_command_does_not_inherit_a_secret(tmp_path):
    result = SubprocessCommandRunner().run(PRINT_ENVIRONMENT, tmp_path)
    assert result is not None
    assert leaked_secrets(result.output.split()) == set()


def test_a_setup_command_keeps_the_variables_it_is_given_and_the_path(tmp_path):
    result = SubprocessCommandRunner().run(PRINT_ENVIRONMENT, tmp_path, {"UV_NO_SYNC": "1"})
    assert result is not None
    assert {"UV_NO_SYNC", "PATH"} <= set(result.output.split())


def test_go_does_not_inherit_a_secret(record, tmp_path, monkeypatch):
    stand_in("go", record, tmp_path, monkeypatch)
    SubprocessGo().build([], tmp_path, {})
    assert started_environment(record) == (set(), set())


def test_go_compiling_its_tests_does_not_inherit_a_secret(record, tmp_path, monkeypatch):
    stand_in("go", record, tmp_path, monkeypatch)
    SubprocessGo().compile_tests([], tmp_path, {"GOWORK": "off"})
    assert started_environment(record) == (set(), set())


def test_cargo_does_not_inherit_a_secret(record, tmp_path, monkeypatch):
    stand_in("cargo", record, tmp_path, monkeypatch)
    SubprocessCargo().build([], tmp_path, {})
    assert started_environment(record) == (set(), set())


def test_rustc_does_not_inherit_a_secret(record, tmp_path, monkeypatch):
    recording_tool(tmp_path / "bin", "rustc", record, output="host: test-triple")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    SubprocessCargo().host(tmp_path)
    assert started_environment(record) == (set(), set())


def test_the_rust_tests_do_not_inherit_a_secret(tmp_path):
    finished = SubprocessTests().run(PRINT_ENVIRONMENT, tmp_path, TEST_LIMIT_MS)
    assert finished is not None
    assert leaked_secrets(finished.output.split()) == set()


def test_gradle_does_not_inherit_a_secret(record, tmp_path):
    recording_tool(tmp_path, "gradlew", record)
    WrapperGradle(tmp_path, tmp_path / "gradle-home", FixedJdk()).run([])
    assert started_environment(record) == (set(), set())


def test_gradle_still_runs_on_the_selected_jdk(record, tmp_path):
    recording_tool(tmp_path, "gradlew", record)
    WrapperGradle(tmp_path, tmp_path / "gradle-home", FixedJdk(Path("/jdks/selected"))).run([])
    assert recorded(record)["JAVA_HOME"] == "/jdks/selected"


def test_the_type_check_does_not_inherit_a_secret(record, tmp_path, monkeypatch):
    stand_in("pnpm", record, tmp_path, monkeypatch)
    PnpmTypeChecker().check(tmp_path)
    assert started_environment(record) == (set(), set())
