"""What a `cstudy` that dies by SIGKILL leaves running (docs/specs/runners.md#process-lifecycle).

Marked `slow`: each test runs `cstudy test` as a real process in a copy of the session's practice
workspace, on code that never returns: a two-sum solution in each runner's language, or a test of a
Go, Rust or Java project's suite, which first creates a marker file. Once the marker exists, or a
debug run printed its ready line, the test kills that one process with SIGKILL, not its group, the
way a crash or `kill -9` ends it. Within two seconds nothing `cstudy` started may still run: no
process in the group of any of its children (the runner and what it started, such as `go test` and
its test binaries, or a Rust test's process), and nothing started from the private directories of
the compiled runners, where a debug server starts the runner in a group of its own.
"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.languages.debug_servers import InstalledDebugServers, this_machine
from coding_study.domain.debugging import DebugSession
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.process_table import (
    POLL_SECONDS,
    Process,
    groups_of_children,
    kill_all,
    left_running,
)
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
LAUNCH = "from coding_study.entrypoints.launcher import main; main()"
CONTENT_PROBLEMS = (
    "0001-two-sum",
    "0251-bank-project-java",
    "0253-bank-project-go",
    "0254-bank-project-rust",
)
HANG_TIMEOUT_SECONDS = 300
"""A cold Rust or Gradle build of a fresh workspace copy comes first, on a busy machine."""
COMPILED = ("go", "rust")
MARKER = "{marker}"
NO_GO = shutil.which("go") is None
NO_CARGO = shutil.which("cargo") is None
DEBUG_SERVERS = InstalledDebugServers(this_machine())
NO_DELVE = NO_GO or DEBUG_SERVERS.delve().path is None
NO_RUST_DEBUG_SERVER = NO_CARGO or DEBUG_SERVERS.lldb_server().path is None

HANGING_TWO_SUM = {
    Language.PYTHON: (
        "python/practice/two_sum.py",
        f"""import time
from pathlib import Path


def two_sum(nums, target):
    Path("{MARKER}").touch()
    while True:
        time.sleep(0.05)
""",
    ),
    Language.TYPESCRIPT: (
        "typescript/practice/two-sum.ts",
        f"""import {{ writeFileSync }} from "node:fs";

export function twoSum(nums: number[], target: number): number[] {{
  writeFileSync("{MARKER}", "");
  for (;;) {{}}
}}
""",
    ),
    Language.JAVA: (
        "jvm/java/src/main/java/practice/two_sum/Solution.java",
        f"""package practice.two_sum;

import java.nio.file.Files;
import java.nio.file.Path;

public class Solution {{
    public int[] twoSum(int[] nums, int target) throws Exception {{
        Files.writeString(Path.of("{MARKER}"), "");
        while (true) {{
            Thread.sleep(50);
        }}
    }}
}}
""",
    ),
    Language.GO: (
        "go/practice/two_sum/two_sum.go",
        f"""package two_sum

import (
	"os"
	"time"
)

func twoSum(nums []int, target int) []int {{
	_ = os.WriteFile("{MARKER}", nil, 0o644)
	for {{
		time.Sleep(50 * time.Millisecond)
	}}
}}
""",
    ),
    Language.RUST: (
        "rust/practice/two_sum.rs",
        f"""pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {{
    let _ = (nums, target);
    std::fs::write("{MARKER}", b"").unwrap();
    loop {{
        std::thread::sleep(std::time::Duration::from_millis(50));
    }}
}}
""",
    ),
}
"""Per runner: the practice file of two-sum, and a solution that marks that it runs, then hangs."""

HANGING_SUITE_TEST = {
    Language.GO: (
        "bank-project-go",
        "hang/hang_test.go",
        f"""package hang

import (
	"os"
	"testing"
	"time"
)

func TestHangs(t *testing.T) {{
	_ = os.WriteFile("{MARKER}", nil, 0o644)
	time.Sleep(time.Hour)
}}
""",
    ),
    Language.RUST: (
        "bank-project-rust",
        "tests/hang.rs",
        f"""#[test]
fn hangs() {{
    std::fs::write("{MARKER}", b"").unwrap();
    loop {{
        std::thread::sleep(std::time::Duration::from_millis(50));
    }}
}}
""",
    ),
    Language.JAVA: (
        "bank-project-java",
        "src/test/java/bank/HangTest.java",
        f"""package bank;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class HangTest {{
    @Test
    void hangs() throws Exception {{
        Files.writeString(Path.of("{MARKER}"), "");
        while (true) {{
            Thread.sleep(50);
        }}
    }}
}}
""",
    ),
}
"""Per project: its slug, a test file of the user's, and a test that marks that it runs, then
hangs: in a `go test` binary the Go runner started, in a Rust test's own process, and in the JVM
that hosts JUnit."""


class KilledRun:
    """A `cstudy test` process, killed alone once its code runs or its debug agent waits."""

    def __init__(self, arguments: list[str], environment: dict[str, str], output: Path) -> None:
        self._stderr_path = output / "stderr.txt"
        with (output / "stdout.txt").open("wb") as stdout, self._stderr_path.open("wb") as stderr:
            self._process = subprocess.Popen(
                [sys.executable, "-c", LAUNCH, "test", *arguments],
                stdout=stdout,
                stderr=stderr,
                env=environment,
                start_new_session=True,
            )

    def wait_until(self, ready: Callable[[], bool]) -> None:
        deadline = time.monotonic() + HANG_TIMEOUT_SECONDS
        while not ready():
            if self._process.poll() is not None or time.monotonic() > deadline:
                stderr = self._stderr_path.read_text()
                pytest.fail(f"never got going; exit {self._process.poll()}:\n{stderr}")
            time.sleep(POLL_SECONDS)

    def printed(self, line: str) -> bool:
        return line in self._stderr_path.read_text().splitlines()

    def kill(self) -> set[int]:
        """SIGKILL to `cstudy` alone; the process groups of the children it had then."""
        children = groups_of_children(self._process.pid)
        self._process.kill()
        self._process.wait()
        return children

    def stop(self) -> None:
        if self._process.poll() is None:
            os.killpg(self._process.pid, signal.SIGKILL)
            self._process.wait()


class Orphans:
    """Starts runs and finds what each left running once killed; kills it all when done."""

    def __init__(self, root: Path, environment: dict[str, str], tmp_path: Path) -> None:
        self._root = root
        self._environment = environment
        self._tmp_path = tmp_path
        self._runs: list[KilledRun] = []
        self._left: list[Process] = []

    def marker(self) -> Path:
        return self._tmp_path / "hanging"

    def write(self, relative: str, template: str) -> Path:
        file = self._root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(template.replace(MARKER, str(self.marker())))
        return file

    def start(self, *arguments: str) -> KilledRun:
        output = self._tmp_path / f"run-{len(self._runs)}"
        output.mkdir()
        run = KilledRun(list(arguments), self._environment, output)
        self._runs.append(run)
        return run

    def left_after_killing(self, run: KilledRun) -> list[str]:
        """What still runs a moment after `cstudy` was killed."""
        private = (self._root / ".cs" / "build" / language / "run" for language in COMPILED)
        left = left_running(run.kill(), private)
        self._left += left
        return [process.command for process in left]

    def kill_everything(self) -> None:
        for run in self._runs:
            run.stop()
        kill_all(self._left)


@pytest.fixture(scope="module")
def content(tmp_path_factory: pytest.TempPathFactory) -> Path:
    content = tmp_path_factory.mktemp("orphan-content")
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    for problem in CONTENT_PROBLEMS:
        shutil.copytree(REPOSITORY_ROOT / "problems" / problem, content / "problems" / problem)
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    return content


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    return workspace_like(practice_workspace, tmp_path_factory.mktemp("orphan") / "ws")


@pytest.fixture
def orphans(
    root: Path, content: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Orphans]:
    """`cstudy`'s environment, set in this process too so that `cstudy start` finds it."""
    for name, value in (
        ("CSTUDY_CONTENT", content),
        ("CSTUDY_WORKSPACE", root),
        ("CSTUDY_CONFIG", tmp_path / "absent-config.toml"),
    ):
        monkeypatch.setenv(name, str(value))
    found = Orphans(root, dict(os.environ), tmp_path)
    yield found
    found.kill_everything()


def start(*arguments: str) -> None:
    started = runner.invoke(cli.app, ["start", *arguments, "--no-open"])
    assert started.exit_code == 0, started.output


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


RUNNERS = [
    Language.PYTHON,
    Language.TYPESCRIPT,
    Language.JAVA,
    pytest.param(Language.GO, marks=pytest.mark.skipif(NO_GO, reason="go is not installed")),
    pytest.param(
        Language.RUST, marks=pytest.mark.skipif(NO_CARGO, reason="cargo is not installed")
    ),
]


@pytest.mark.parametrize("language", RUNNERS)
def test_a_runner_with_a_hanging_case_ends_with_a_killed_cstudy(orphans, language):
    start("two-sum", "--lang", language)
    file = orphans.write(*HANGING_TWO_SUM[language])
    run = orphans.start(str(file))
    run.wait_until(orphans.marker().exists)
    assert orphans.left_after_killing(run) == []


PROJECT_SUITES = [
    pytest.param(Language.GO, marks=pytest.mark.skipif(NO_GO, reason="go is not installed")),
    pytest.param(
        Language.RUST, marks=pytest.mark.skipif(NO_CARGO, reason="cargo is not installed")
    ),
    Language.JAVA,
]


@pytest.mark.parametrize("language", PROJECT_SUITES)
def test_a_project_suite_with_a_hanging_test_ends_with_a_killed_cstudy(orphans, language):
    slug, test_file, template = HANGING_SUITE_TEST[language]
    start(slug)
    orphans.write(f"projects/{slug}/{test_file}", template)
    run = orphans.start(slug)
    run.wait_until(orphans.marker().exists)
    assert orphans.left_after_killing(run) == []


DEBUGGED = [
    Language.PYTHON,
    pytest.param(
        Language.GO, marks=pytest.mark.skipif(NO_DELVE, reason="go or dlv is not installed")
    ),
    pytest.param(
        Language.RUST,
        marks=pytest.mark.skipif(NO_RUST_DEBUG_SERVER, reason="cargo or a debug server is missing"),
    ),
]


@pytest.mark.parametrize("language", DEBUGGED)
def test_a_debug_run_waiting_for_the_ide_ends_with_a_killed_cstudy(orphans, language):
    """The agent holds the runner before it runs anything: Delve and `debugserver` hold it in a
    process of their own, and `debugserver` in a process group of its own too."""
    start("two-sum", "--lang", language)
    file = orphans.write(*HANGING_TWO_SUM[language])
    port = free_port()
    run = orphans.start(str(file), "--debug", "--debug-port", str(port))
    ready_line = DebugSession(language, port).ready_line
    run.wait_until(lambda: run.printed(ready_line))
    assert orphans.left_after_killing(run) == []
