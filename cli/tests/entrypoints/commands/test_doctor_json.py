"""`cstudy doctor --json` (docs/specs/cli.md#cstudy-doctor)."""

import json
from collections.abc import Callable

import pytest
from typer.testing import CliRunner

from coding_study.application.doctor import CheckResult, CheckStatus, DoctorReport
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import doctor
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import mark_workspace

runner = CliRunner()
NOTICE = "warming Gradle daemon (first run)"
NODE = CheckResult("node", CheckStatus.OK, "v24.18.0 (type stripping)")
VENV = CheckResult("python/.venv", CheckStatus.FAIL, "missing", "cstudy doctor --fix")
GRADLE = CheckResult("gradle", CheckStatus.WARN, "not found", "brew install gradle")


def stub_report(monkeypatch: pytest.MonkeyPatch, *results: CheckResult) -> None:
    def report(_environment: object, notify: Callable[[str], None]) -> DoctorReport:
        notify(NOTICE)
        return DoctorReport(results)

    monkeypatch.setattr(doctor, "run_doctor", report)


def invoke(*arguments: str):
    return runner.invoke(cli.app, [*arguments, "doctor", "--json"])


def document(*arguments: str):
    return json.loads(invoke(*arguments).stdout)


def test_each_check_is_a_row_of_name_status_detail_and_fix(monkeypatch):
    stub_report(monkeypatch, NODE, VENV)
    assert document()["checks"] == [
        {"name": "node", "status": "ok", "detail": "v24.18.0 (type stripping)", "fix": None},
        {
            "name": "python/.venv",
            "status": "fail",
            "detail": "missing",
            "fix": "cstudy doctor --fix",
        },
    ]


def test_a_check_without_detail_has_an_empty_detail(monkeypatch):
    stub_report(monkeypatch, CheckResult("projects", CheckStatus.OK))
    assert document()["checks"][0]["detail"] == ""


def test_a_warning_is_lower_case(monkeypatch):
    stub_report(monkeypatch, GRADLE)
    assert document()["checks"][0]["status"] == "warn"


def test_only_ok_and_warn_pass(monkeypatch):
    stub_report(monkeypatch, NODE, GRADLE)
    assert document()["passed"] is True


def test_a_failure_does_not_pass(monkeypatch):
    stub_report(monkeypatch, NODE, VENV)
    assert document()["passed"] is False


def test_a_failure_exits_4(monkeypatch):
    stub_report(monkeypatch, VENV)
    assert invoke().exit_code == ExitCode.ENVIRONMENT_ERROR


def test_without_a_failure_it_exits_0(monkeypatch):
    stub_report(monkeypatch, NODE, GRADLE)
    assert invoke().exit_code == ExitCode.SUCCESS


def test_progress_notices_go_to_standard_error(monkeypatch):
    stub_report(monkeypatch, NODE)
    assert invoke().stderr == f"{NOTICE}\n"


def test_outside_a_workspace_the_workspace_is_null(monkeypatch, tmp_path):
    stub_report(monkeypatch, NODE)
    assert document("--workspace", str(tmp_path / "nowhere"))["workspace"] is None


def test_in_a_workspace_the_document_names_it(monkeypatch, tmp_path):
    workspace = mark_workspace(tmp_path / "ws")
    stub_report(monkeypatch, NODE)
    assert document("--workspace", str(workspace))["workspace"] == str(workspace)


def test_json_with_fix_is_a_usage_error(monkeypatch):
    stub_report(monkeypatch, NODE)
    result = runner.invoke(cli.app, ["doctor", "--json", "--fix"])
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: --json excludes --fix\n",
    )
