"""What user code inherits when `cstudy test` runs it, through the real runners
(docs/specs/runners.md#process-environment): the problem's code writes its own environment to a
file, and a secret in the shell that ran `cstudy` is not in it, while what the toolchain needed
to get that far is.

Each language starts two-sum in a copy of the session's practice workspace, and one test per
language shows the same two things; a language whose toolchain is missing is skipped.
"""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from tests.helpers import CATALOG_PROBLEMS, REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.launch_environment import leaked_secrets, missing_needs, plant_secrets, recorded
from tests.toolchains import jvm_marked
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
MARKER = "@MARKER@"
SLUG = "two-sum"
USER_FILES = {
    "python": (
        "python/practice/two_sum.py",
        f"""import os
from pathlib import Path


def two_sum(nums, target):
    lines = (f"{{name}}={{value}}\\n" for name, value in os.environ.items())
    Path("{MARKER}").write_text("".join(lines))
    return []
""",
    ),
    "typescript": (
        "typescript/practice/two-sum.ts",
        f"""import {{ writeFileSync }} from "node:fs";

export function twoSum(nums: number[], target: number): number[] {{
  const lines = Object.entries(process.env).map(([name, value]) => `${{name}}=${{value}}\\n`);
  writeFileSync("{MARKER}", lines.join(""));
  return [];
}}
""",
    ),
    "java": (
        "jvm/java/src/main/java/practice/two_sum/Solution.java",
        f"""package practice.two_sum;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Collectors;

public class Solution {{
    public int[] twoSum(int[] nums, int target) throws Exception {{
        var lines = System.getenv().entrySet().stream()
            .map(entry -> entry.getKey() + "=" + entry.getValue() + "\\n")
            .collect(Collectors.joining());
        Files.writeString(Path.of("{MARKER}"), lines);
        return new int[0];
    }}
}}
""",
    ),
    "kotlin": (
        "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt",
        f"""package practice.two_sum

import java.io.File

class Solution {{
    fun twoSum(nums: IntArray, target: Int): IntArray {{
        val lines = System.getenv().entries.joinToString("") {{ "${{it.key}}=${{it.value}}\\n" }}
        File("{MARKER}").writeText(lines)
        return intArrayOf()
    }}
}}
""",
    ),
    "go": (
        "go/practice/two_sum/two_sum.go",
        f"""package two_sum

import (
	"os"
	"strings"
)

func twoSum(nums []int, target int) []int {{
	text := strings.Join(os.Environ(), "\\n") + "\\n"
	_ = os.WriteFile("{MARKER}", []byte(text), 0o644)
	return nil
}}
""",
    ),
    "rust": (
        "rust/practice/two_sum.rs",
        f"""pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {{
    let _ = (nums, target);
    let lines = std::env::vars().map(|(name, value)| format!("{{name}}={{value}}\\n"));
    let text: String = lines.collect();
    std::fs::write("{MARKER}", text).unwrap();
    vec![]
}}
""",
    ),
}
"""Per language: the practice file of two-sum, and a solution that writes its environment to the
marker and returns the wrong answer, which does not matter here."""
TOOLCHAINS = {"go": "go", "rust": "cargo"}
"""The command a language needs on PATH beyond what the practice workspace holds."""


class Practice:
    """`cstudy` in a workspace of its own, over a content root holding two-sum."""

    def __init__(self, root: Path, marker_directory: Path) -> None:
        self.root = root
        self.marker_directory = marker_directory

    def environment_seen_by(self, language: str) -> dict[str, str]:
        marker = self.marker_directory / f"{language}.environment"
        start = cs("start", SLUG, "--lang", language, "--no-open")
        assert start.exit_code == 0, start.output
        relative, text = USER_FILES[language]
        (self.root / relative).write_text(text.replace(MARKER, str(marker)), encoding="utf-8")
        tested = cs("test", SLUG, "--lang", language)
        assert marker.is_file(), tested.output
        return recorded(marker)


def cs(*arguments: str):
    return runner.invoke(cli.app, list(arguments))


@pytest.fixture(scope="module")
def practice(
    tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path
) -> Iterator[Practice]:
    content = tmp_path_factory.mktemp("environment-content")
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(CATALOG_PROBLEMS / "0001-two-sum", content / "problems" / "0001-two-sum")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("environment") / "ws")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CSTUDY_CONTENT", str(content))
        patch.setenv("CSTUDY_WORKSPACE", str(root))
        patch.setenv("CSTUDY_CONFIG", str(content / "absent-config.toml"))
        plant_secrets(patch)
        yield Practice(root, tmp_path_factory.mktemp("environment-markers"))


@pytest.fixture(scope="module", params=jvm_marked(USER_FILES))
def seen(request: pytest.FixtureRequest, practice: Practice) -> dict[str, str]:
    """What the user code of one language found in its environment."""
    language: str = request.param
    command = TOOLCHAINS.get(language)
    if command is not None and shutil.which(command) is None:
        pytest.skip(f"{command} is not installed")
    return practice.environment_seen_by(language)


def test_user_code_does_not_inherit_a_secret(seen):
    assert leaked_secrets(seen) == set()


def test_user_code_still_finds_what_its_toolchain_needed(seen):
    assert missing_needs(seen) == set()
