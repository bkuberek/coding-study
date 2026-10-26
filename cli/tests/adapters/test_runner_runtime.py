"""The per-workspace copy of the runners (installation-and-workspaces.md#runner-runtime)."""

import os
from pathlib import Path

import pytest

from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS, RunnerRuntime
from coding_study.domain.errors import RunnerStartError

SOURCES = {
    "python/pyproject.toml": "[project]\n",
    "python/src/cs_runner/__main__.py": "print('runner')\n",
    "python/tests/test_runner.py": "def test(): ...\n",
    "typescript/runner.ts": "export {};\n",
    "typescript/node_modules/typescript/index.js": "",
    "jvm/settings.gradle.kts": 'rootProject.name = "cs-jvm"\n',
    "jvm/runner/build/libs/runner.jar": "",
    "jvm/.gradle/state": "",
    "conformance/9001-x/meta.yaml": "id: '9001'\n",
}
OLD_NS = 1_000_000_000
LAUNCHER = ".cs/runtime/ide/cstudy-launcher.jar"


@pytest.fixture
def runners(tmp_path: Path) -> Path:
    for relative, text in SOURCES.items():
        path = tmp_path / "content" / "runners" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path / "content" / "runners"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    return workspace


@pytest.fixture
def runtime(runners: Path, workspace: Path) -> RunnerRuntime:
    return RunnerRuntime(runners, workspace)


def copied(workspace: Path) -> set[str]:
    root = workspace / RUNTIME_RUNNERS
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def test_the_runtime_lives_in_the_workspace(runtime, workspace):
    assert runtime.directory == workspace / ".cs" / "runtime" / "runners"


def test_ensure_copies_the_runner_sources(runtime, workspace):
    runtime.ensure()
    assert copied(workspace) == {
        "python/pyproject.toml",
        "python/src/cs_runner/__main__.py",
        "typescript/runner.ts",
        "jvm/settings.gradle.kts",
    }


def test_a_new_workspace_is_not_current(runtime):
    assert runtime.is_current() is False


def test_ensure_makes_it_current(runtime):
    runtime.ensure()
    assert runtime.is_current() is True


def test_a_changed_source_makes_it_stale(runtime, runners):
    runtime.ensure()
    (runners / "typescript" / "runner.ts").write_text("export const changed = 1;\n")
    assert runtime.is_current() is False


def test_ensure_rewrites_a_changed_source(runtime, runners, workspace):
    runtime.ensure()
    (runners / "typescript" / "runner.ts").write_text("export const changed = 1;\n")
    runtime.ensure()
    text = (workspace / RUNTIME_RUNNERS / "typescript" / "runner.ts").read_text()
    assert text == "export const changed = 1;\n"


def test_ensure_keeps_the_timestamps_of_unchanged_files(runtime, runners, workspace):
    runtime.ensure()
    unchanged = workspace / RUNTIME_RUNNERS / "jvm" / "settings.gradle.kts"
    os.utime(unchanged, ns=(OLD_NS, OLD_NS))
    (runners / "typescript" / "runner.ts").write_text("export const changed = 1;\n")
    runtime.ensure()
    assert unchanged.stat().st_mtime_ns == OLD_NS


def test_ensure_deletes_a_removed_source(runtime, runners, workspace):
    runtime.ensure()
    (runners / "typescript" / "runner.ts").unlink()
    runtime.ensure()
    assert "typescript/runner.ts" not in copied(workspace)


def test_ensure_keeps_build_output_in_the_runtime(runtime, runners, workspace):
    runtime.ensure()
    output = workspace / RUNTIME_RUNNERS / "jvm" / "runner" / "build" / "classes" / "Main.class"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"\xca\xfe")
    (runners / "typescript" / "runner.ts").write_text("export const changed = 1;\n")
    runtime.ensure()
    assert output.is_file()


def test_a_current_runtime_is_left_alone(runtime, workspace):
    runtime.ensure()
    stamp = workspace / ".cs" / "runtime" / "stamp.json"
    os.utime(stamp, ns=(OLD_NS, OLD_NS))
    runtime.ensure()
    assert stamp.stat().st_mtime_ns == OLD_NS


def test_a_missing_runners_directory_is_a_start_error(workspace, tmp_path):
    with pytest.raises(RunnerStartError, match="runners"):
        RunnerRuntime(tmp_path / "nowhere", workspace).ensure()


def test_ensure_installs_the_ide_launcher(runtime, workspace):
    runtime.ensure()
    assert (workspace / LAUNCHER).is_file()


def test_a_missing_ide_launcher_makes_it_stale(runtime, workspace):
    runtime.ensure()
    (workspace / LAUNCHER).unlink()
    assert runtime.is_current() is False


def test_ensure_restores_the_ide_launcher_of_an_up_to_date_copy(runtime, workspace):
    runtime.ensure()
    (workspace / LAUNCHER).unlink()
    runtime.ensure()
    assert (workspace / LAUNCHER).is_file()
