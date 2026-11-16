"""A workspace of one language is healthy after `cstudy doctor --fix`
(docs/specs/cli.md#rows-by-language): `cstudy init --lang <language>`, `doctor --fix`, then
`doctor --json` in a temporary workspace reports no `fail`, and no `warn` outside the machine-level
rows, with the rows of the other languages left out. A language whose toolchain is missing is
skipped."""

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from coding_study.adapters.jdk_locator import EnvJdkSelector
from coding_study.domain.jdk import SUPPORTED_JDKS
from coding_study.entrypoints import cli
from tests.helpers import REPOSITORY_ROOT
from tests.toolchains import jvm_marked

pytestmark = pytest.mark.slow

runner = CliRunner()
LANGUAGES = ["python", "typescript", *jvm_marked(["java", "go", "rust"])]
MACHINE_ROWS = {"docker", "docker leftovers", "installs"}
"""Rows that describe the machine and may warn whatever the workspace holds."""
TOOL_ROWS = {"java": {"gradle"}, "go": {"dlv"}, "rust": {"debugserver", "lldb-server"}}
"""Tools that only `cstudy test --debug` (the debug servers) or regenerating the Gradle wrapper
(Homebrew Gradle) need, which a machine may lack: their rows warn, never fail."""
LEFT_OUT_ROWS = {
    "python": {"node", "pnpm", "java", "gradle", "go", "rustc", "cargo", "runner typescript"},
    "typescript": {
        "uv",
        "java",
        "gradle",
        "go",
        "rustc",
        "cargo",
        "runner python",
        "python pytest",
    },
    "java": {"uv", "node", "pnpm", "go", "rustc", "cargo", "runner python", "runner kotlin"},
    "go": {
        "uv",
        "node",
        "pnpm",
        "java",
        "gradle",
        "rustc",
        "cargo",
        "runner python",
        "jvm/gradlew",
    },
    "rust": {"uv", "node", "pnpm", "java", "gradle", "go", "dlv", "runner python", "jvm/gradlew"},
}
MINIMUM_GO = (1, 25)
GO_VERSION = re.compile(r"go(\d+)\.(\d+)")


def skip_without_toolchain(language: str) -> None:
    """Skips the test for a language whose toolchain this machine lacks."""
    needs = {
        "python": ("uv",),
        "typescript": ("node", "pnpm"),
        "java": (),
        "go": ("go",),
        "rust": ("cargo", "rustc"),
    }
    for tool in needs[language]:
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} is not installed")
    if language == "java":
        selected = EnvJdkSelector(os.environ).selected()
        if selected is None or selected.feature < SUPPORTED_JDKS.minimum:
            pytest.skip("no JDK 21 or newer is selected")
    if language == "go" and not _go_is_recent():
        pytest.skip("Go 1.25 or newer is not installed")


def _go_is_recent() -> bool:
    done = subprocess.run(["go", "version"], capture_output=True, text=True, check=False)
    found = GO_VERSION.search(done.stdout)
    return found is not None and (int(found[1]), int(found[2])) >= MINIMUM_GO


def cs(workspace: Path, *arguments: str):
    return runner.invoke(cli.app, ["--workspace", str(workspace), *arguments])


@pytest.fixture(scope="module", params=LANGUAGES)
def doctor_rows(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[tuple[str, dict[str, dict[str, Any]]]]:
    """The language and the rows of `doctor --json` after init and `doctor --fix`."""
    language: str = request.param
    skip_without_toolchain(language)
    workspace = tmp_path_factory.mktemp("one-language") / "ws"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CSTUDY_CONTENT", str(REPOSITORY_ROOT))
        patch.setenv("CSTUDY_CONFIG", str(workspace.parent / "absent-config.toml"))
        initialized = runner.invoke(
            cli.app, ["init", str(workspace), "--lang", language, "--no-ide"]
        )
        assert initialized.exit_code == 0, initialized.output
        fixed = cs(workspace, "doctor", "--fix")
        assert fixed.exit_code == 0, fixed.output
        report = cs(workspace, "doctor", "--json")
        document = json.loads(report.stdout)
        assert document["workspace"] == str(workspace.resolve()), report.output
        yield language, {check["name"]: check for check in document["checks"]}


def test_nothing_fails(doctor_rows):
    _language, rows = doctor_rows
    assert {name for name, row in rows.items() if row["status"] == "fail"} == set()


def test_nothing_warns_outside_the_machine_level_rows(doctor_rows):
    language, rows = doctor_rows
    allowed = MACHINE_ROWS | TOOL_ROWS.get(language, set())
    assert {name for name, row in rows.items() if row["status"] == "warn"} - allowed == set()


def test_the_languages_row_names_the_one_language(doctor_rows):
    language, rows = doctor_rows
    row = rows["languages"]
    # A default_lang other than the language is named in the row, which stays ok.
    assert (row["status"], row["detail"].split(" (")[0]) == ("ok", language)


def test_the_rows_of_the_other_languages_are_left_out(doctor_rows):
    language, rows = doctor_rows
    assert LEFT_OUT_ROWS[language] & set(rows) == set()


def test_only_the_chosen_languages_folders_exist(doctor_rows):
    language, rows = doctor_rows
    assert rows["workspace"]["status"] == "ok"
    root = Path(rows["workspace"]["detail"].split(" (")[0])
    folders = {"python", "typescript", "jvm", "go", "rust"}
    own = {"java": "jvm"}.get(language, language)
    assert {name for name in folders if (root / name).exists()} == {own}
