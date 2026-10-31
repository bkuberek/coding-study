"""`cstudy submit` output and JSON document (docs/specs/cli.md#cstudy-submit)."""

import json

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.domain.runs import CaseOutcome, Returned, RunCase, RunJob, UserError
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import submit as submit_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS, PROJECT_PROBLEMS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

runner = CliRunner()
CASES = json.loads(
    (PROJECT_PROBLEMS / "0001-bank-project-python" / "tests.json").read_text(encoding="utf-8")
)["cases"]
EXPECTED = {case["id"]: case["expected"] for case in CASES}
HEADER = f"{PROJECT_SLUG} · python · submit level 1 of 2"
TRANSFER = "transfer(timestamp: int, source_id: str, target_id: str, amount: int) -> int"


def correct(job: RunJob, case: RunCase) -> CaseOutcome:
    return Returned(EXPECTED[case.id], 1000)


def wrong_on(*case_ids: str):
    def answer(job: RunJob, case: RunCase) -> CaseOutcome:
        return Returned(["wrong"], 1000) if case.id in case_ids else correct(job, case)

    return answer


@pytest.fixture
def process() -> ScriptedProjectProcess:
    return ScriptedProjectProcess(answer=correct)


@pytest.fixture
def environment(tmp_path, monkeypatch, process):
    environment = project_environment(tmp_path, process)
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    monkeypatch.setattr(submit_command, "load_environment", lambda *_: environment)
    return environment


def as_mock(environment) -> None:
    """A fresh attempt started by `cstudy mock`."""
    start_attempt(environment, StartRequest(PROJECT_SLUG, fresh=True, mock=True))


def cs_submit(*arguments: str):
    return runner.invoke(cli.app, ["submit", *arguments])


def lines(*arguments: str) -> list[str]:
    return cs_submit(*arguments).output.splitlines()


def document(*arguments: str) -> dict:
    return json.loads(cs_submit("--json", *arguments).stdout)


def test_a_pass_of_the_unlocked_level_opens_the_next(environment):
    assert lines() == [
        HEADER,
        "",
        "level 1  PASS     3/3 (1 visible, 2 hidden)",
        "PASS     ex1   level 1",
        "",
        "3/3 passed · level 2 unlocked: Transfers",
        f"add        {TRANSFER}",
        "tests      tests/test_level_2.py (1 test)",
        f"statement  .statements/{PROJECT_SLUG}.md (updated)",
    ]


def test_a_passing_submission_exits_0(environment):
    assert cs_submit().exit_code == ExitCode.SUCCESS


def test_a_failing_hidden_case_shows_its_input_in_practice(environment, process):
    process.answer = wrong_on("h3")
    cs_submit()
    assert lines()[2:10] == [
        "level 1  PASS     3/3 (1 visible, 2 hidden)",
        "level 2  FAIL     2/3 (1 visible, 2 hidden)",
        "PASS     ex1   level 1",
        "PASS     ex2   level 2",
        "FAIL     h3    hidden · level 2",
        '         input     ops=["Bank", "create_account", "transfer"]  '
        'args=[[], [1, "ivy"], [2, "ivy", "zed", 1]]',
        "         expected  [null, true, -1]",
        '         actual    ["wrong"]',
    ]


def test_a_failing_submission_says_what_opens_the_next_level(environment, process):
    process.answer = wrong_on("h2")
    assert lines()[-1] == "2/3 passed · level 2 opens when level 1 passes"


def test_a_failing_submission_exits_1(environment, process):
    process.answer = wrong_on("h2")
    assert cs_submit().exit_code == ExitCode.FAILURES


def test_a_mock_attempt_only_counts_failing_hidden_cases(environment, process):
    as_mock(environment)
    process.answer = wrong_on("h2")
    assert lines()[2:5] == [
        "level 1  FAIL     2/3 (1 visible, 2 hidden) · 1 hidden case failed",
        "PASS     ex1   level 1",
        "",
    ]


def test_a_failing_visible_case_shows_its_input_in_a_mock_attempt_too(environment, process):
    as_mock(environment)
    process.answer = wrong_on("ex1")
    assert lines()[3] == "FAIL     ex1   level 1"


def test_the_full_pass_points_to_cstudy_done(environment):
    cs_submit()
    assert lines()[-2:] == [
        "6/6 passed",
        "all passed · every level done. Next: cstudy done --rating easy|ok|hard",
    ]


def test_a_lower_level_says_it_counts_for_nothing(environment):
    cs_submit()
    assert lines("--level", "1")[-1] == (
        "3/3 passed · level 1 only: opens no level and does not count for cstudy done"
    )


def test_a_locked_level_exits_3(environment):
    result = cs_submit("--level", "2")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: level 2 is locked; pass level 1 with cstudy submit first\n",
    )


def test_code_that_does_not_load_exits_2(environment, process):
    process.load_error = UserError("SymbolNotFound", "bank.bank has no class Bank")
    assert cs_submit().exit_code == ExitCode.USER_CODE_ERROR


def test_code_that_does_not_load_shows_the_load_error(environment, process):
    process.load_error = UserError("SymbolNotFound", "bank.bank has no class Bank")
    assert lines()[3:] == [
        "ERROR    load  SymbolNotFound: bank.bank has no class Bank",
        "",
        "0/3 passed · the code did not load",
    ]


def test_another_kind_of_problem_exits_3(tmp_path, monkeypatch):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS), toolchains=toolchains
    )
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    monkeypatch.setattr(submit_command, "load_environment", lambda *_: environment)
    result = cs_submit()
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: cstudy submit is for project problems; cstudy test grades two-sum\n",
    )


def test_json_describes_the_submission(environment):
    found = document()
    assert {key: found[key] for key in ("slug", "mode", "outcome", "exit_code", "every_level")} == {
        "slug": PROJECT_SLUG,
        "mode": "new",
        "outcome": "passed",
        "exit_code": 0,
        "every_level": True,
    }


def test_json_names_the_opened_level_and_its_methods(environment):
    assert document()["levels"] == {
        "graded_up_to": 1,
        "last": 2,
        "unlocked": 2,
        "newly_unlocked": True,
        "methods_added": [TRANSFER],
    }


def test_json_tallies_each_level(environment):
    assert document()["level_tallies"] == [
        {
            "level": 1,
            "total": 3,
            "passed": 3,
            "visible_total": 1,
            "visible_passed": 1,
            "hidden_total": 2,
            "hidden_passed": 2,
        }
    ]


def test_json_cases_carry_their_level(environment):
    assert [(case["id"], case["level"]) for case in document()["cases"]] == [
        ("ex1", 1),
        ("h1", 1),
        ("h2", 1),
    ]


def test_json_of_a_mock_attempt_leaves_hidden_cases_out(environment, process):
    as_mock(environment)
    process.answer = wrong_on("h2")
    assert [case["id"] for case in document()["cases"]] == ["ex1"]


def test_json_of_code_that_does_not_load_names_the_error(environment, process):
    process.load_error = UserError("SymbolNotFound", "bank.bank has no class Bank")
    found = document()
    assert (found["outcome"], found["load_error"]["type"], found["cases"]) == (
        "load_failed",
        "SymbolNotFound",
        [],
    )
