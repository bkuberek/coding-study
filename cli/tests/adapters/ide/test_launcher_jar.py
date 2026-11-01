"""The committed launcher jar: rebuilt from tools/ide-launcher/ it has the same bytes, and it runs
cstudy like a shell would (docs/decisions/0010-ide-integration.md)."""

import hashlib
import os
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


def jdk_tool(name: str) -> str | None:
    """`name` of the JDK that JAVA_HOME names, else of the first on PATH: where build.sh looks."""
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        tool = Path(java_home) / "bin" / name
        return str(tool) if os.access(tool, os.X_OK) else None
    return shutil.which(name)


def javac_feature_release() -> str | None:
    javac = jdk_tool("javac")
    if javac is None or jdk_tool("jar") is None:
        return None
    version = subprocess.run([javac, "-version"], capture_output=True, text=True, check=True)
    printed = (version.stdout or version.stderr).strip()
    return printed.removeprefix("javac ").split(".")[0]


def jdk_home_reporting(directory: Path, version: str) -> Path:
    """A JDK home whose `javac` only reports `version`, and whose `jar` is never reached."""
    for name, body in (("javac", f'echo "javac {version}" >&2'), ("jar", "exit 1")):
        tool = directory / "bin" / name
        tool.parent.mkdir(parents=True, exist_ok=True)
        tool.write_text(f"#!/bin/sh\n{body}\n")
        tool.chmod(0o755)
    return directory


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
        pytest.skip(
            f"needs javac {REQUIRED_JAVAC} and jar (found javac {release}); "
            f"select a JDK {REQUIRED_JAVAC} with JAVA_HOME"
        )
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


def build(java_home: Path | str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "JAVA_HOME": str(java_home)}
    command = ["bash", str(BUILD_SCRIPT), str(tmp_path / "cstudy-launcher.jar")]
    return subprocess.run(command, env=environment, capture_output=True, text=True, check=False)


def test_the_build_uses_the_javac_of_java_home(tmp_path):
    completed = build(jdk_home_reporting(tmp_path / "jdk", "26.0.2"), tmp_path)
    assert "found: javac 26.0.2" in completed.stderr


def test_a_javac_of_another_release_ends_the_build_with_exit_2(tmp_path):
    completed = build(jdk_home_reporting(tmp_path / "jdk", "26.0.2"), tmp_path)
    assert (completed.returncode, "needs javac 21" in completed.stderr) == (2, True)


def test_a_javac_of_another_release_says_how_to_select_a_jdk_21(tmp_path):
    completed = build(jdk_home_reporting(tmp_path / "jdk", "26.0.2"), tmp_path)
    assert "select a JDK 21 with JAVA_HOME" in completed.stderr


def test_a_java_home_without_javac_ends_the_build_with_exit_2(tmp_path):
    assert build(tmp_path / "no-jdk", tmp_path).returncode == 2


def test_a_java_home_without_javac_says_where_it_looked(tmp_path):
    completed = build(tmp_path / "no-jdk", tmp_path)
    assert f"no javac in {tmp_path / 'no-jdk'}/bin/" in completed.stderr


def test_a_java_home_without_javac_says_how_to_select_a_jdk_21(tmp_path):
    assert "select a JDK 21 with JAVA_HOME" in build(tmp_path / "no-jdk", tmp_path).stderr
