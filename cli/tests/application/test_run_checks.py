"""What the web UI checks before it starts a run or a job, worded as the CLI words each refusal
(docs/specs/web-ui.md#lifecycle, docs/specs/web-ui.md#jobs)."""

import shutil
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import OverlayProblemFiles, OverlayProblemRepository
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.run_checks import (
    RunCheck,
    RunCommand,
    RunSubject,
    check_run,
    check_verify_scope,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.errors import (
    AttemptEndedError,
    UnknownAttemptError,
    UnknownProblemError,
    UsageError,
)
from coding_study.domain.problem import Language, ProblemKind
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
OWN_PROBLEM = "problems/5001-two-sum"


@pytest.fixture
def practice(tmp_path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    return make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))


@pytest.fixture
def project(tmp_path) -> Environment:
    return project_environment(tmp_path, ScriptedProjectProcess())


def started(environment: Environment, slug: str, language: Language | None = None) -> int:
    return start_attempt(environment, StartRequest(slug, language)).attempt.id


def refusal(environment: Environment, check: RunCheck) -> str:
    with pytest.raises(UsageError) as refused:
        check_run(environment, check)
    return str(refused.value)


# runs


def test_a_test_run_names_the_attempts_problem_language_and_kind(practice):
    attempt_id = started(practice, "two-sum", Language.PYTHON)
    subject = check_run(practice, RunCheck(attempt_id, RunCommand.TEST))
    assert subject == RunSubject("two-sum", Language.PYTHON, ProblemKind.FUNCTION)


def test_a_submission_of_a_project_names_its_problem(project):
    attempt_id = started(project, PROJECT_SLUG)
    subject = check_run(project, RunCheck(attempt_id, RunCommand.SUBMIT))
    assert subject == RunSubject(PROJECT_SLUG, Language.PYTHON, ProblemKind.PROJECT)


def test_an_unknown_attempt_is_refused(practice):
    with pytest.raises(UnknownAttemptError):
        check_run(practice, RunCheck(99, RunCommand.TEST))


def test_an_attempt_another_one_replaced_is_refused(practice):
    attempt_id = started(practice, "two-sum", Language.PYTHON)
    start_attempt(practice, StartRequest("two-sum", Language.PYTHON, fresh=True))
    with pytest.raises(AttemptEndedError):
        check_run(practice, RunCheck(attempt_id, RunCommand.TEST))


def test_an_item_has_no_runs(practice):
    attempt_id = start_item_attempt(practice, ItemStartRequest("url-shortener")).attempt.id
    message = refusal(practice, RunCheck(attempt_id, RunCommand.TEST))
    assert message == "url-shortener is not autograded"


def test_submit_on_another_kind_is_refused_as_cstudy_submit_refuses_it(practice):
    attempt_id = started(practice, "two-sum", Language.PYTHON)
    message = refusal(practice, RunCheck(attempt_id, RunCommand.SUBMIT))
    assert message == "cstudy submit is for project problems; cstudy test grades two-sum"


def test_a_locked_level_is_refused(project):
    attempt_id = started(project, PROJECT_SLUG)
    message = refusal(project, RunCheck(attempt_id, RunCommand.SUBMIT, level=2))
    assert message == "level 2 is locked; pass level 1 with cstudy submit first"


def test_the_unlocked_level_is_accepted(project):
    attempt_id = started(project, PROJECT_SLUG)
    subject = check_run(project, RunCheck(attempt_id, RunCommand.TEST, level=1))
    assert subject.slug == PROJECT_SLUG


def test_a_level_on_a_problem_without_levels_is_refused(practice):
    attempt_id = started(practice, "two-sum", Language.PYTHON)
    message = refusal(practice, RunCheck(attempt_id, RunCommand.TEST, level=1))
    assert message == "two-sum has no levels"


# jobs


@pytest.fixture
def overlay(tmp_path) -> Environment:
    """A catalog holding lru-cache, and a workspace whose own problem is two-sum."""
    catalog = repository_root(tmp_path / "catalog", PRACTICE)
    shutil.rmtree(catalog / "problems" / "0001-two-sum")
    workspace = repository_root(tmp_path / "workspace", PRACTICE)
    shutil.rmtree(workspace / "problems" / "0002-lru-cache")
    (workspace / "problems" / "0001-two-sum").rename(workspace / OWN_PROBLEM)
    meta = workspace / OWN_PROBLEM / "meta.yaml"
    meta.write_text(meta.read_text().replace('id: "0001"', 'id: "5001"'))
    return make_environment(
        workspace,
        content_root=catalog,
        problems=OverlayProblemRepository(FsProblemRepository(catalog), workspace),
        files=OverlayProblemFiles(FsProblemFiles(catalog), workspace),
    )


def test_your_own_problems_may_be_verified(overlay):
    check_verify_scope(overlay, ("two-sum",))


def test_a_catalog_problem_is_verified_in_a_content_checkout(overlay):
    with pytest.raises(UsageError) as refused:
        check_verify_scope(overlay, ("two-sum", "lru-cache"))
    assert str(refused.value) == (
        "the page verifies your own problems; "
        "run cstudy verify in a content checkout for catalog problems"
    )


def test_an_unknown_problem_is_not_found(overlay):
    with pytest.raises(UnknownProblemError):
        check_verify_scope(overlay, ("no-such-problem",))
