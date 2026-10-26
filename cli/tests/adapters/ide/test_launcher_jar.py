"""The committed launcher jar: rebuilt from tools/ide-launcher/ it has the same bytes, and it runs
cstudy like a shell would (docs/decisions/0010-ide-integration.md)."""

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from coding_study.adapters.ide.launcher import launcher_jar
from tests.helpers import REPOSITORY_ROOT

BUILD_SCRIPT = REPOSITORY_ROOT / "tools" / "ide-launcher" / "build.sh"
REQUIRED_JAVAC = "21"
"""build.sh's `required_javac`: javac 17 emits other bytes for the same `--release 17`."""
NOT_FOUND = 127
FAKE_EXIT = 3
FAKE_CSTUDY = f"""#!/bin/sh
printf '%s\\n' "$@"
exit {FAKE_EXIT}
"""

pytestmark = pytest.mark.slow


def javac_feature_release() -> str | None:
    if shutil.which("javac") is None or shutil.which("jar") is None:
        return None
    version = subprocess.run(["javac", "-version"], capture_output=True, text=True, check=True)
    printed = (version.stdout or version.stderr).strip()
    return printed.removeprefix("javac ").split(".")[0]


def run_launcher(arguments: list[str], environment: dict[str, str], tmp_path: Path):
    jar = tmp_path / "cstudy-launcher.jar"
    jar.write_bytes(launcher_jar())
    # The JVM takes user.home from the password database on macOS, not from HOME.
    command = ["java", f"-Duser.home={environment['HOME']}", "-jar", str(jar), *arguments]
    return subprocess.run(command, env=environment, capture_output=True, text=True, check=False)


@pytest.fixture
def fake_cstudy(tmp_path: Path) -> Path:
    script = tmp_path / "bin" / "cstudy"
    script.parent.mkdir()
    script.write_text(FAKE_CSTUDY)
    script.chmod(0o755)
    return script


@pytest.fixture
def bare_environment(tmp_path: Path) -> dict[str, str]:
    """No cstudy anywhere the launcher looks, and java still reachable."""
    java = shutil.which("java")
    if java is None:
        pytest.skip("needs java on PATH")
    home = tmp_path / "home"
    home.mkdir()
    return {"PATH": str(Path(java).resolve().parent), "HOME": str(home)}


def test_a_rebuild_reproduces_the_committed_jar(tmp_path):
    release = javac_feature_release()
    if release != REQUIRED_JAVAC:
        pytest.skip(f"needs javac {REQUIRED_JAVAC} and jar on PATH (found javac {release})")
    rebuilt = tmp_path / "cstudy-launcher.jar"
    subprocess.run(["bash", str(BUILD_SCRIPT), str(rebuilt)], check=True, capture_output=True)
    digests = {hashlib.sha256(data).hexdigest() for data in (rebuilt.read_bytes(), launcher_jar())}
    assert len(digests) == 1


def test_the_launcher_passes_the_arguments_through(fake_cstudy, bare_environment, tmp_path):
    environment = {**bare_environment, "CSTUDY_EXECUTABLE": str(fake_cstudy)}
    completed = run_launcher(["test", "/a path/two_sum.py"], environment, tmp_path)
    assert completed.stdout.splitlines() == ["test", "/a path/two_sum.py"]


def test_the_launcher_exits_with_the_cstudy_exit_code(fake_cstudy, bare_environment, tmp_path):
    environment = {**bare_environment, "CSTUDY_EXECUTABLE": str(fake_cstudy)}
    assert run_launcher(["show"], environment, tmp_path).returncode == FAKE_EXIT


def test_the_launcher_finds_cstudy_in_the_uv_tool_directory(
    fake_cstudy, bare_environment, tmp_path
):
    environment = {**bare_environment, "UV_TOOL_BIN_DIR": str(fake_cstudy.parent)}
    assert run_launcher(["show"], environment, tmp_path).returncode == FAKE_EXIT


def test_without_cstudy_the_launcher_exits_127(bare_environment, tmp_path):
    completed = run_launcher(["show"], bare_environment, tmp_path)
    assert (completed.returncode, "CSTUDY_EXECUTABLE" in completed.stderr) == (NOT_FOUND, True)
