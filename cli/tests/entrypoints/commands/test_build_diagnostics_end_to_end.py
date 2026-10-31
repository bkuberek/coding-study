"""`cstudy test --events` on a single-file problem that does not compile, through the real Gradle,
Go and Cargo toolchains: the compiler's report is a `diagnostic` at the user's file and line
(docs/specs/cli.md#diagnostics).

Each language's two-sum is started in a copy of the session's practice workspace and given a
file with one error: a name the compiler cannot find.
"""

import json
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from tests.helpers import CATALOG_PROBLEMS, REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
PROBLEM = "0001-two-sum"


@dataclass(frozen=True, slots=True)
class BrokenFile:
    language: str
    toolchain: str
    path: str
    source: str
    line: int
    """The line of the unknown name."""


BROKEN_FILES = (
    BrokenFile(
        "java",
        "java",
        "jvm/java/src/main/java/practice/two_sum/Solution.java",
        "package practice.two_sum;\n\npublic class Solution {\n"
        "    public int[] twoSum(int[] nums, int target) {\n        return missing;\n    }\n}\n",
        5,
    ),
    BrokenFile(
        "kotlin",
        "java",
        "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt",
        "package practice.two_sum\n\nclass Solution {\n"
        "    fun twoSum(nums: IntArray, target: Int): IntArray {\n"
        "        return missing\n    }\n}\n",
        5,
    ),
    BrokenFile(
        "go",
        "go",
        "go/practice/two_sum/two_sum.go",
        "package two_sum\n\nfunc twoSum(nums []int, target int) []int {\n\treturn missing\n}\n",
        4,
    ),
    BrokenFile(
        "rust",
        "cargo",
        "rust/practice/two_sum.rs",
        "pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {\n    missing\n}\n",
        2,
    ),
)


class Practice:
    """`cstudy` in a workspace of its own, over a content root holding two-sum."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def broken_events(self, broken: BrokenFile) -> list[dict]:
        started = runner.invoke(
            cli.app, ["start", "two-sum", "--lang", broken.language, "--no-open"]
        )
        assert started.exit_code == 0, started.output
        (self.root / broken.path).write_text(broken.source, encoding="utf-8")
        result = runner.invoke(cli.app, ["test", "two-sum", "--lang", broken.language, "--events"])
        return [json.loads(line) for line in result.stdout.splitlines()]


@pytest.fixture(scope="module")
def practice(
    tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path
) -> Iterator[Practice]:
    content = tmp_path_factory.mktemp("build-diagnostics-content")
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(CATALOG_PROBLEMS / PROBLEM, content / "problems" / PROBLEM)
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("build-diagnostics") / "ws")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CSTUDY_CONTENT", str(content))
        patch.setenv("CSTUDY_WORKSPACE", str(root))
        patch.setenv("CSTUDY_CONFIG", str(content / "absent-config.toml"))
        yield Practice(root)


@pytest.fixture(scope="module", params=BROKEN_FILES, ids=lambda broken: broken.language)
def broken(request: pytest.FixtureRequest) -> BrokenFile:
    if shutil.which(request.param.toolchain) is None:
        pytest.skip(f"{request.param.toolchain} is not installed")
    return request.param


@pytest.fixture(scope="module")
def found(practice: Practice, broken: BrokenFile) -> list[dict]:
    return practice.broken_events(broken)


def test_a_compile_error_is_a_build_diagnostic_at_the_users_file_and_line(broken, found):
    (diagnostic,) = [event for event in found if event["type"] == "diagnostic"][:1]
    assert (diagnostic["source"], diagnostic["file"], diagnostic["line"]) == (
        "build",
        broken.path,
        broken.line,
    )


def test_a_compile_error_names_a_column(found):
    diagnostic = next(event for event in found if event["type"] == "diagnostic")
    assert isinstance(diagnostic["column"], int)


def test_the_message_is_the_compilers_without_the_place(found):
    diagnostic = next(event for event in found if event["type"] == "diagnostic")
    assert "missing" in diagnostic["message"]
    assert diagnostic["file"] not in diagnostic["message"]


def test_the_run_ends_build_failed(found):
    assert (found[-1]["outcome"], found[-1]["exit_code"]) == ("build_failed", 2)
