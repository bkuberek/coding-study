"""The Java and Kotlin project fixtures 9026 to 9029, and the Kotlin projects on the virtual clock
9043 and 9044 (whose stress workers call suspend methods), through `cstudy verify --conformance`.

Marked `slow`: each fixture's folder builds with Gradle, grades on the main runtime classpath and
runs its JUnit Platform suite in a JVM, as a user's project does, in a copy of the session's
practice workspace over this checkout's content (docs/specs/runners.md#conformance-suite).
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.languages.jvm.runner import COLD_DAEMON_NOTICE
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT
from tests.workspaces import workspace_like

pytestmark = [pytest.mark.slow, pytest.mark.jvm]

runner = CliRunner()
FIXTURES = {
    "java": ("conformance-project-java", "conformance-suite-junit-java"),
    "kotlin": (
        "conformance-project-kotlin",
        "conformance-suite-junit-kotlin",
        "conformance-project-clock-kotlin",
        "conformance-project-stress-clock-kotlin",
    ),
}
RESULTS = {
    "java": [
        "9026-conformance-project-java      java ok",
        "9028-conformance-suite-junit-java  java ok",
    ],
    "kotlin": [
        "9027-conformance-project-kotlin               kt ok",
        "9029-conformance-suite-junit-kotlin           kt ok",
        "9043-conformance-project-clock-kotlin         kt ok",
        "9044-conformance-project-stress-clock-kotlin  kt ok",
    ],
}


@pytest.mark.parametrize("language", ["java", "kotlin"])
def test_the_jvm_runner_meets_the_project_expectations(
    practice_workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, language: str
):
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(REPOSITORY_ROOT))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))
    arguments = ["verify", "--conformance", "--lang", language, *FIXTURES[language]]
    result = runner.invoke(cli.app, arguments)
    expected = RESULTS[language]
    lines = [line for line in result.output.splitlines() if line != COLD_DAEMON_NOTICE]
    assert (result.exit_code, lines[: len(expected)]) == (ExitCode.SUCCESS, expected)
