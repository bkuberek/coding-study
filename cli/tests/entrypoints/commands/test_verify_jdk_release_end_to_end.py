"""`cstudy verify` builds a Java reference at the problem's minimum release, through real Gradle
(docs/specs/runners.md#the-jdk-and-the-release-level).

Marked `slow`. The fixture problem's reference uses stream gatherers, an API of JDK 24: it fails at
the default minimum, JDK 21, and passes once the problem declares `jdk: {min: 24}`, on any JDK from
24 to 26. On a JDK below 24 the declared problem is skipped instead. Run this module once per JDK.
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.jdk_locator import shell_jdk
from coding_study.domain.jdk import SUPPORTED_JDKS
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "jdk-range" / "problems"
SLUG = "pair-sums"
GATHERERS_MINIMUM = 24
"""Stream gatherers became final in JDK 24."""


def selected_feature() -> int:
    selected = shell_jdk().selected()
    assert selected is not None, "these tests need a JDK: set JAVA_HOME or put java on PATH"
    return selected.feature


@pytest.fixture(autouse=True)
def a_supported_jdk() -> None:
    if not SUPPORTED_JDKS.contains(selected_feature()):
        pytest.skip("the selected JDK is outside the supported range")


@pytest.fixture
def verify(tmp_path: Path, practice_workspace: Path, monkeypatch: pytest.MonkeyPatch):
    """`cstudy verify pair-sums --lang java`, over a content root of the fixture problem, which
    declares `jdk` when the test says so."""
    content = tmp_path / "content"
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(FIXTURES, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(content))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))
    meta = content / "problems" / "0001-pair-sums" / "meta.yaml"

    def run(declaration: str | None = None):
        if declaration is not None:
            meta.write_text(f"{meta.read_text()}jdk: {declaration}\n")
        return runner.invoke(cli.app, ["verify", SLUG, "--lang", "java"])

    return run


def test_a_reference_using_a_newer_api_fails_at_the_default_minimum(verify):
    result = verify()
    assert result.exit_code == ExitCode.FAILURES, result.output
    assert "references do not build" in result.output
    assert "Gatherers" in result.output


@pytest.mark.skipif(
    selected_feature() < GATHERERS_MINIMUM, reason="stream gatherers need JDK 24 to compile"
)
def test_the_same_reference_passes_once_the_problem_declares_the_minimum(verify):
    result = verify("{min: 24}")
    assert result.exit_code == ExitCode.SUCCESS, result.output
    assert "java 1/1 ok" in result.output


@pytest.mark.skipif(
    selected_feature() >= GATHERERS_MINIMUM, reason="the declared range holds the selected JDK"
)
def test_a_jdk_below_the_declared_minimum_skips_the_problem(verify):
    result = verify("{min: 24}")
    assert result.exit_code == ExitCode.SUCCESS, result.output
    assert f"skipped  java: runs on JDK 24 to 26; JAVA_HOME selects JDK {selected_feature()}" in (
        result.output
    )
