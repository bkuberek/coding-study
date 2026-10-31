from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.doctor import (
    JVM_FIX,
    PYTHON_FIX,
    TYPESCRIPT_FIX,
    CheckResult,
    CheckStatus,
    ContentLocation,
    DoctorReport,
    FixOutcome,
    NotFound,
    PracticeWorkspace,
)
from coding_study.application.ports import ProbeResult, ScaffoldOutcome
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import doctor
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT, mark_workspace

runner = CliRunner()


def stub_report(monkeypatch: pytest.MonkeyPatch, *results: CheckResult) -> None:
    def report(_environment: object, notify: Callable[[str], None]) -> DoctorReport:
        notify("warming Gradle daemon (first run)")
        return DoctorReport(results)

    monkeypatch.setattr(doctor, "run_doctor", report)


def stub_fixes(monkeypatch: pytest.MonkeyPatch, *outcomes: FixOutcome) -> list[str]:
    """Replaces the fix use case; returns the projects it was asked to fix."""
    asked: list[str] = []

    def fix(
        workspace: PracticeWorkspace,
        _content: ContentLocation | NotFound,
        _notify: Callable[[str], None],
    ) -> tuple[FixOutcome, ...]:
        asked.append(str(workspace.files.root))
        return outcomes

    monkeypatch.setattr(doctor, "fix_workspace", fix)
    monkeypatch.setattr(doctor, "repair_workspace", lambda *_: ScaffoldOutcome((), ()))
    return asked


def test_doctor_prints_one_line_per_check(monkeypatch):
    stub_report(
        monkeypatch,
        CheckResult("node", CheckStatus.OK, "v24.18.0 (type stripping)"),
        CheckResult("workspace", CheckStatus.WARN, "no workspace here"),
    )
    result = runner.invoke(cli.app, ["doctor"])
    assert result.output.splitlines()[1:] == [
        "ok    node v24.18.0 (type stripping)",
        "WARN  workspace no workspace here",
    ]


def test_doctor_prints_the_fix_after_a_failure(monkeypatch):
    stub_report(
        monkeypatch,
        CheckResult("python/.venv", CheckStatus.FAIL, "missing", "cstudy doctor --fix"),
    )
    result = runner.invoke(cli.app, ["doctor"])
    assert (
        result.output.splitlines()[-1] == "FAIL  python/.venv missing    fix: cstudy doctor --fix"
    )


def test_doctor_exits_0_with_only_ok_and_warn(monkeypatch):
    stub_report(monkeypatch, CheckResult("gradle", CheckStatus.WARN, "not found"))
    assert runner.invoke(cli.app, ["doctor"]).exit_code == 0


def test_doctor_exits_4_on_any_failure(monkeypatch):
    stub_report(monkeypatch, CheckResult("java", CheckStatus.FAIL, "17.0.9 (need JDK 21)"))
    assert runner.invoke(cli.app, ["doctor"]).exit_code == ExitCode.ENVIRONMENT_ERROR == 4


def test_no_color_flag_is_accepted(monkeypatch):
    stub_report(monkeypatch, CheckResult("uv", CheckStatus.OK, "0.10.11"))
    assert runner.invoke(cli.app, ["--no-color", "doctor"]).output.endswith("ok    uv 0.10.11\n")


def test_doctor_prints_progress_notices_first(monkeypatch):
    stub_report(monkeypatch, CheckResult("uv", CheckStatus.OK, "0.10.11"))
    output = runner.invoke(cli.app, ["doctor"]).output
    assert output.splitlines()[0] == "warming Gradle daemon (first run)"


def test_fix_runs_before_the_checks_and_reports_each_command(monkeypatch, tmp_path):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(mark_workspace(tmp_path)))
    stub_report(monkeypatch, CheckResult("uv", CheckStatus.OK, "0.10.11"))
    stub_fixes(monkeypatch, FixOutcome(PYTHON_FIX, ProbeResult(0, "Resolved 3 packages\n")))
    lines = runner.invoke(cli.app, ["doctor", "--fix"]).output.splitlines()
    assert lines[0] == "ok    uv sync (in python)"


def test_failed_fix_prints_the_end_of_its_output(monkeypatch, tmp_path):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(mark_workspace(tmp_path)))
    stub_report(monkeypatch)
    failed = FixOutcome(TYPESCRIPT_FIX, ProbeResult(1, "Progress\nERR_PNPM_FETCH_404\n"))
    stub_fixes(monkeypatch, failed)
    lines = runner.invoke(cli.app, ["doctor", "--fix"]).output.splitlines()
    assert lines[:3] == [
        "FAIL  pnpm install (in typescript) exited with 1",
        "      Progress",
        "      ERR_PNPM_FETCH_404",
    ]


def test_failed_fix_exits_4_even_when_the_checks_pass(monkeypatch, tmp_path):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(mark_workspace(tmp_path)))
    stub_report(monkeypatch, CheckResult("uv", CheckStatus.OK, "0.10.11"))
    stub_fixes(monkeypatch, FixOutcome(JVM_FIX, None))
    assert runner.invoke(cli.app, ["doctor", "--fix"]).exit_code == ExitCode.ENVIRONMENT_ERROR


def test_fix_outside_a_workspace_is_a_usage_error(monkeypatch, tmp_path):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(tmp_path / "nowhere"))
    stub_report(monkeypatch)
    assert runner.invoke(cli.app, ["doctor", "--fix"]).exit_code == ExitCode.USAGE_ERROR


def test_the_workspace_flag_picks_the_workspace_to_fix(monkeypatch, tmp_path):
    workspace = mark_workspace(tmp_path / "ws")
    stub_report(monkeypatch)
    asked = stub_fixes(monkeypatch)
    runner.invoke(cli.app, ["--workspace", str(workspace), "doctor", "--fix"])
    assert asked == [str(workspace)]


def test_fix_restores_missing_workspace_files_first(monkeypatch, tmp_path):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(mark_workspace(tmp_path)))
    stub_report(monkeypatch)
    monkeypatch.setattr(doctor, "fix_workspace", lambda *_: ())
    lines = runner.invoke(cli.app, ["doctor", "--fix"]).output.splitlines()
    assert "restored jvm/settings.gradle.kts" in lines


def test_fix_never_overwrites_a_practice_file(monkeypatch, tmp_path):
    workspace = mark_workspace(tmp_path)
    practice = workspace / "python" / "practice" / "two_sum.py"
    practice.parent.mkdir(parents=True)
    practice.write_text("def two_sum(): ...\n")
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(workspace))
    stub_report(monkeypatch)
    monkeypatch.setattr(doctor, "fix_workspace", lambda *_: ())
    runner.invoke(cli.app, ["doctor", "--fix"])
    assert practice.read_text() == "def two_sum(): ...\n"


def test_fix_refreshes_the_runner_runtime(monkeypatch, tmp_path):
    workspace = mark_workspace(tmp_path)
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(workspace))
    stub_report(monkeypatch)
    monkeypatch.setattr(doctor, "fix_workspace", lambda *_: ())
    runner.invoke(cli.app, ["doctor", "--fix"])
    assert (workspace / ".cs" / "runtime" / "runners" / "jvm" / "settings.gradle.kts").is_file()


def test_fix_recreates_a_dangling_project_link(monkeypatch, tmp_path):
    workspace = mark_workspace(tmp_path)
    project = workspace / "projects" / "bank-project-python"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text("[tool.ruff]\n")
    (project / ".venv").symlink_to("/moved/away/.venv", target_is_directory=True)
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(workspace))
    stub_report(monkeypatch)
    monkeypatch.setattr(doctor, "fix_workspace", lambda *_: ())
    lines = runner.invoke(cli.app, ["doctor", "--fix"]).output.splitlines()
    relinked = "relinked projects/bank-project-python/.venv" in lines
    assert (relinked, (project / ".venv").readlink()) == (True, Path("../../python/.venv"))


def test_doctor_environment_reports_a_missing_workspace(tmp_path):
    workspace = doctor.doctor_environment(tmp_path, {}, tmp_path).workspace
    assert isinstance(workspace, NotFound)
    assert workspace.unusable is False


def test_a_workspace_with_a_newer_schema_is_unusable(tmp_path):
    marker = mark_workspace(tmp_path) / ".cs" / "workspace.toml"
    marker.write_text('schema = 2\ncreated_with = "9.0.0"\n')
    workspace = doctor.doctor_environment(tmp_path, {}, tmp_path).workspace
    assert isinstance(workspace, NotFound)
    assert workspace.unusable is True


def test_doctor_environment_reads_the_marker_version(tmp_path):
    mark_workspace(tmp_path, created_with="0.0.9")
    environment = doctor.doctor_environment(tmp_path, {}, tmp_path)
    assert isinstance(environment.workspace, PracticeWorkspace)
    assert environment.workspace.created_with == "0.0.9"


def test_doctor_environment_finds_the_checkout_content(tmp_path):
    content = doctor.doctor_environment(tmp_path, {}, tmp_path).content
    assert isinstance(content, ContentLocation)
    assert (content.files.root, content.editable) == (REPOSITORY_ROOT, True)
