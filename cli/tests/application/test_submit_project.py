"""`cstudy submit` grades a project problem and opens its next level
(docs/specs/cli.md#cstudy-submit, progress-and-scheduling.md#project-attempts)."""

import json
from dataclasses import replace
from datetime import timedelta

import pytest

from coding_study.application.environment import Environment
from coding_study.application.project_tests import LevelTestFile
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest, submit_project
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.runs import CaseOutcome, Returned, RunCase, RunJob, UserError
from coding_study.domain.submissions import LevelTally, LevelUnlock
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS, PROJECT_PROBLEMS
from tests.project_fakes import (
    PROJECT_FOLDER,
    PROJECT_SLUG,
    ScriptedProjectProcess,
    project_environment,
)

CASES = json.loads(
    (PROJECT_PROBLEMS / "0001-bank-project-python" / "tests.json").read_text(encoding="utf-8")
)["cases"]
EXPECTED = {case["id"]: case["expected"] for case in CASES}
LEVEL_1 = ["ex1", "h1", "h2"]
LEVEL_2_TESTS = f"{PROJECT_FOLDER}/tests/test_level_2.py"
STATEMENT = f".statements/{PROJECT_SLUG}.md"
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
def environment(tmp_path, process) -> Environment:
    environment = project_environment(tmp_path, process)
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment


def submit(environment: Environment, **fields: object):
    request = replace(SubmitRequest(), **fields)  # type: ignore[arg-type]
    return submit_project(environment, request, [].append)


def attempt(environment: Environment):
    found = environment.progress.active_attempt()
    assert found is not None
    return found


def test_another_kind_of_problem_is_a_usage_error(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS), toolchains=toolchains
    )
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    with pytest.raises(
        UsageError, match="cstudy submit is for project problems; cstudy test grades two-sum"
    ):
        submit(environment)


def test_every_case_of_the_unlocked_levels_is_graded(environment, process):
    submit(environment)
    assert [case.id for case in process.gradings[0].cases] == LEVEL_1


def test_a_submission_is_stored_with_a_tally_per_level(environment):
    submit(environment)
    (stored,) = environment.progress.submissions(attempt(environment).id)
    assert stored.levels == (LevelTally(1, 1, 1, 2, 2),)


def test_a_submission_hashes_the_project_folder_it_graded(environment, process):
    process.answer = wrong_on("h2")
    submit(environment)
    (stored,) = environment.progress.submissions(attempt(environment).id)
    assert stored.code_hash == environment.workspace.content_hash(PROJECT_FOLDER)


def test_a_submission_of_every_unlocked_level_says_so(environment):
    submit(environment)
    (stored,) = environment.progress.submissions(attempt(environment).id)
    assert (stored.graded_up_to, stored.every_level) == (1, True)


def test_a_full_pass_of_the_unlocked_levels_opens_the_next(environment):
    submit(environment)
    assert attempt(environment).level_unlocked == 2


def test_an_opened_level_is_recorded(environment):
    submit(environment)
    assert environment.progress.level_unlocks(attempt(environment).id)[-1] == LevelUnlock(
        attempt(environment).id, 2, NOW
    )


def test_an_opened_level_gets_its_test_file(environment):
    submit(environment)
    assert environment.workspace.exists(LEVEL_2_TESTS)


def test_an_opened_level_shows_in_the_statement(environment):
    submit(environment)
    assert "is locked" not in environment.workspace.read_text(STATEMENT)


def test_an_opened_level_names_the_methods_it_adds(environment):
    opened = submit(environment).opened
    assert opened is not None
    assert opened.methods == (TRANSFER,)


def test_an_opened_level_reports_its_test_file(environment):
    opened = submit(environment).opened
    assert opened is not None
    assert opened.tests == LevelTestFile(2, "tests/test_level_2.py", 1, True)


def test_a_failing_submission_opens_nothing(environment, process):
    process.answer = wrong_on("h2")
    assert submit(environment).opened is None


def test_a_failing_submission_keeps_the_level(environment, process):
    process.answer = wrong_on("h2")
    submit(environment)
    assert attempt(environment).level_unlocked == 1


def test_a_failing_submission_is_stored_too(environment, process):
    process.answer = wrong_on("h2")
    submit(environment)
    (stored,) = environment.progress.submissions(attempt(environment).id)
    assert stored.tally == Tally(total=3, passed=2, failed=1)


def test_a_locked_level_is_a_usage_error(environment):
    with pytest.raises(
        UsageError, match="level 2 is locked; pass level 1 with cstudy submit first"
    ):
        submit(environment, level=2)


def test_a_lower_level_is_stored_without_counting(environment):
    submit(environment)
    submit(environment, level=1)
    stored = environment.progress.submissions(attempt(environment).id)[-1]
    assert (stored.graded_up_to, stored.every_level) == (1, False)


def test_a_lower_level_opens_nothing(environment):
    submit(environment)
    submit(environment, level=1)
    assert attempt(environment).level_unlocked == 2


def test_one_submission_opens_one_level(environment):
    submit(environment)
    submit(environment)
    assert attempt(environment).level_unlocked == 2


def test_a_full_pass_of_every_level_is_the_first_pass(environment):
    submit(environment)
    submit(environment)
    assert attempt(environment).first_pass_at == NOW


def test_a_full_pass_of_every_level_opens_nothing_more(environment):
    submit(environment)
    assert submit(environment).opened is None


def test_a_pass_before_the_last_level_is_not_the_first_pass(environment):
    submit(environment)
    assert attempt(environment).first_pass_at is None


def test_code_that_does_not_load_is_stored_with_every_case_errored(environment, process):
    process.load_error = UserError("SymbolNotFound", "bank.bank has no class Bank")
    submit(environment)
    (stored,) = environment.progress.submissions(attempt(environment).id)
    assert stored.tally == Tally(total=3, errored=3)


def test_code_that_does_not_load_opens_nothing(environment, process):
    process.load_error = UserError("SymbolNotFound", "bank.bank has no class Bank")
    assert submit(environment).opened is None


def test_submissions_over_the_time_box_are_still_graded(environment):
    environment.progress.update_attempt(replace(attempt(environment), time_limit_s=60))
    environment.clock.advance(timedelta(hours=2))
    assert submit(environment).opened is not None


def test_the_result_counts_the_levels_after_the_submission(environment):
    levels = submit(environment).levels
    assert (levels.ran_up_to, levels.unlocked, levels.newly_unlocked) == (1, 2, True)
