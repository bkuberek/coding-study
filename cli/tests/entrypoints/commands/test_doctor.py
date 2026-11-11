import re
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.serve_install import InstalledWebUi
from coding_study.adapters.sqlite.progress_database import SqliteProgressDatabase
from coding_study.adapters.sqlite.schema import latest_schema_version
from coding_study.application.doctor import (
    JVM_FIX,
    PYTEST_FIX,
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
from coding_study.application.ports import (
    JdkSelector,
    NotInstalled,
    ProbeResult,
    ScaffoldOutcome,
)
from coding_study.application.preferences import read_preferences
from coding_study.domain.code_intelligence import BASEDPYRIGHT, LanguageServer, License
from coding_study.domain.jdk import JdkSource, SelectedJdk
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import doctor
from coding_study.entrypoints.shared import ExitCode
from coding_study.entrypoints.web import STATIC_DIRECTORY
from tests.helpers import REPOSITORY_ROOT, mark_workspace, progress_database_at

runner = CliRunner()
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


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
        _jdk: JdkSelector,
        _notify: Callable[[str], None],
        _consent: Callable[[LanguageServer, License], bool],
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
    stub_report(
        monkeypatch,
        CheckResult("java", CheckStatus.FAIL, "17.0.9 (too old: cstudy supports JDK 21 to 26)"),
    )
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


def test_a_notice_of_the_fix_goes_to_standard_output_where_a_job_relays_it(monkeypatch, tmp_path):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(mark_workspace(tmp_path)))
    stub_report(monkeypatch)
    note = "skipped the language servers: code intelligence is off"
    monkeypatch.setattr(doctor, "repair_workspace", lambda *_: ScaffoldOutcome((), ()))
    monkeypatch.setattr(doctor, "fix_workspace", lambda _w, _c, _j, notify, _a: notify(note) or ())
    result = runner.invoke(cli.app, ["doctor", "--fix"])
    assert (note in result.stdout, note in result.stderr) == (True, False)


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


def test_the_fix_help_says_it_installs_the_language_servers():
    output = runner.invoke(cli.app, ["doctor", "--help"]).output
    help_text = " ".join(ANSI_ESCAPE.sub("", output).replace("│", " ").split())
    assert (
        "While the code_intelligence preference is on, also install the language servers "
        "for code intelligence into .cs/lsp/." in help_text
    )


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


def test_doctor_environment_selects_the_jdk_its_environment_names(tmp_path):
    home = tmp_path / "jdk"
    (home / "bin").mkdir(parents=True)
    (home / "bin" / "java").write_text("#!/bin/sh\n")
    (home / "bin" / "java").chmod(0o755)
    (home / "release").write_text('JAVA_VERSION="26.0.1"\n')
    environment = doctor.doctor_environment(tmp_path, {"JAVA_HOME": str(home)}, tmp_path)
    assert environment.jdk.selected() == SelectedJdk("26.0.1", 26, JdkSource.JAVA_HOME)


def test_doctor_environment_finds_the_checkout_content(tmp_path):
    content = doctor.doctor_environment(tmp_path, {}, tmp_path).content
    assert isinstance(content, ContentLocation)
    assert (content.files.root, content.editable) == (REPOSITORY_ROOT, True)


def test_doctor_environment_checks_the_installed_web_ui(tmp_path):
    web = doctor.doctor_environment(tmp_path, {}, tmp_path).web
    assert web.assets() == InstalledWebUi(STATIC_DIRECTORY).assets()


def test_doctor_environment_reads_the_preferences_of_the_workspace(tmp_path):
    mark_workspace(tmp_path)
    preferences = tmp_path / ".cs" / "serve" / "preferences.json"
    preferences.parent.mkdir(parents=True)
    preferences.write_text('{"format": 1, "code_intelligence": true}\n')
    workspace = doctor.doctor_environment(tmp_path, {}, tmp_path).workspace
    assert isinstance(workspace, PracticeWorkspace)
    assert read_preferences(workspace.preferences).code_intelligence is True


def test_doctor_environment_locates_the_servers_in_the_workspaces_lsp_directory(tmp_path):
    mark_workspace(tmp_path)
    workspace = doctor.doctor_environment(tmp_path, {}, tmp_path).workspace
    assert isinstance(workspace, PracticeWorkspace)
    assert workspace.language_servers.probe(BASEDPYRIGHT) == NotInstalled()


def test_doctor_environment_installs_the_servers_with_the_same_adapter(tmp_path):
    mark_workspace(tmp_path)
    workspace = doctor.doctor_environment(tmp_path, {}, tmp_path).workspace
    assert isinstance(workspace, PracticeWorkspace)
    assert workspace.language_server_installer is workspace.language_servers


def make_cstudy(prefix: Path, version: str) -> Path:
    script = prefix / "bin" / "cstudy"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    (prefix / "pyvenv.cfg").write_text("home = /usr/bin\n")
    dist_info = (
        prefix / "lib" / "python3.13" / "site-packages" / f"coding_study-{version}.dist-info"
    )
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(f"Name: coding-study\nVersion: {version}\n")
    return script


def test_doctor_environment_scans_the_path_its_environment_names(tmp_path):
    first = make_cstudy(tmp_path / "uv" / "tools" / "coding-study", "0.1.0")
    second = make_cstudy(tmp_path / "Cellar" / "cstudy" / "0.11.1" / "libexec", "0.11.1")
    environ = {
        "PATH": f"{first.parent}:{second.parent}",
        "UV_TOOL_DIR": str(tmp_path / "uv" / "tools"),
    }
    scan = doctor.doctor_environment(tmp_path, environ, tmp_path).installs.scan()
    assert [(i.kind.value, i.version) for i in scan.on_path] == [
        ("uv tool", "0.1.0"),
        ("Homebrew", "0.11.1"),
    ]


def test_doctor_environment_names_the_running_install(tmp_path):
    running = doctor.doctor_environment(tmp_path, {}, tmp_path).installs.scan().running
    assert running.prefix == Path(sys.prefix).resolve()


def test_a_failed_fix_prints_what_to_do_by_hand(monkeypatch, tmp_path):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(mark_workspace(tmp_path)))
    stub_report(monkeypatch)
    stub_fixes(monkeypatch, FixOutcome(PYTEST_FIX, ProbeResult(2, "error sending request\n")))
    lines = runner.invoke(cli.app, ["doctor", "--fix"]).output.splitlines()
    assert lines[0].endswith(f"    fix: {PYTEST_FIX.manual}")


def test_a_failed_fix_without_a_manual_step_prints_no_fix(monkeypatch, tmp_path):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(mark_workspace(tmp_path)))
    stub_report(monkeypatch)
    stub_fixes(monkeypatch, FixOutcome(PYTHON_FIX, ProbeResult(1, "")))
    lines = runner.invoke(cli.app, ["doctor", "--fix"]).output.splitlines()
    assert "fix:" not in lines[0]


def test_fix_migrates_an_older_progress_database(monkeypatch, tmp_path):
    workspace = mark_workspace(tmp_path)
    progress_database_at(workspace / "progress.db", 4)
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(workspace))
    stub_report(monkeypatch)
    monkeypatch.setattr(doctor, "fix_workspace", lambda *_: ())
    lines = runner.invoke(cli.app, ["doctor", "--fix"]).output.splitlines()
    assert "migrated progress.db from schema 4 to 6" in lines
    assert (
        SqliteProgressDatabase(workspace / "progress.db").schema().found == latest_schema_version()
    )


def test_doctor_environment_reads_the_progress_database_the_config_names(tmp_path):
    mark_workspace(tmp_path)
    progress_database_at(tmp_path / "state.db", 4)
    config = tmp_path / "config.toml"
    config.write_text('progress_db = "state.db"\n')
    environment = doctor.doctor_environment(tmp_path, {"CSTUDY_CONFIG": str(config)}, tmp_path)
    assert isinstance(environment.workspace, PracticeWorkspace)
    assert environment.workspace.progress.schema().found == 4


def test_doctor_environment_reads_the_default_progress_database_when_the_config_is_invalid(
    tmp_path,
):
    mark_workspace(tmp_path)
    progress_database_at(tmp_path / "progress.db", 4)
    config = tmp_path / "config.toml"
    config.write_text("progress_db = 5\n")
    environment = doctor.doctor_environment(tmp_path, {"CSTUDY_CONFIG": str(config)}, tmp_path)
    assert isinstance(environment.workspace, PracticeWorkspace)
    assert environment.workspace.progress.schema().found == 4
