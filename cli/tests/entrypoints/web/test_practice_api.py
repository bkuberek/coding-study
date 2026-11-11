"""Starting an attempt, revealing hints and finishing from the page, through the use cases
`cstudy start`, `cstudy hint` and `cstudy done` call (docs/specs/web-ui.md#attempts)."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.adapters.languages.rust.test_generator import RustTestGenerator
from coding_study.application.attempt_status import attempt_status
from coding_study.application.environment import Environment
from coding_study.application.ide_files import IdeRequest
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus, RunRecord
from coding_study.domain.ide import Ide
from coding_study.domain.jdk import JDK_FIX
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from coding_study.entrypoints.commands.ide import write_ide_files
from coding_study.entrypoints.commands.status import status_document
from coding_study.entrypoints.web.markdown import render_markdown
from tests.fakes import (
    NOW,
    FakeStubGenerator,
    FakeToolchains,
    jdk_of,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_TRACKS, RUST_PROJECT_PROBLEMS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.web_server import WRITE_HEADERS, session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
ATTEMPTS = "/api/v1/attempts"
FIRST_HINT = "For each value, which partner would complete the sum?"
SOLVE_TIME = timedelta(minutes=18, seconds=40)
TWO_SUM_CASES = 4
KOTLIN_AND_PYTHON = (Language.KOTLIN, Language.PYTHON)
PROJECT_HINTS = """
## Hints

### Hint 1

Keep balances in a dictionary.

### Hint 2

Check both accounts before moving money.
"""


@pytest.fixture
def practice(tmp_path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    return make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))


@pytest.fixture
def python_attempt(practice) -> Attempt:
    return start_attempt(practice, StartRequest("two-sum", Language.PYTHON)).attempt


@pytest.fixture
def project(tmp_path) -> Environment:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    problem_md = tmp_path / "problems" / "0001-bank-project-python" / "problem.md"
    problem_md.write_text(problem_md.read_text(encoding="utf-8") + PROJECT_HINTS, encoding="utf-8")
    return environment


def post(tmp_path: Path, environment: Environment, path: str, body: object = None):
    with session_client(web_app(tmp_path, environment)) as client:
        return client.post(path, json=body if body is not None else {}, headers=WRITE_HEADERS)


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def message(response) -> str:
    return response.json()["error"]["message"]


def in_progress(environment: Environment, slug: str, language: Language | None) -> Attempt:
    found = environment.progress.in_progress_attempt(slug, language)
    assert found is not None
    return found


def record_full_pass(environment: Environment, attempt: Attempt) -> None:
    tally = Tally(total=TWO_SUM_CASES, passed=TWO_SUM_CASES)
    environment.progress.add_test_run(RunRecord(attempt.id, NOW, "hash", tally, 10))
    environment.progress.update_attempt(replace(attempt, first_pass_at=NOW))


# start


def test_a_start_answers_201_with_the_attempts_status(tmp_path, practice):
    response = post(tmp_path, practice, ATTEMPTS, {"slug": "two-sum", "language": "python"})
    attempt = in_progress(practice, "two-sum", Language.PYTHON)
    expected = status_document(attempt_status(practice, "two-sum", Language.PYTHON))
    assert (response.status_code, response.json(), attempt.id) == (
        201,
        expected,
        response.json()["attempt_id"],
    )


def test_a_start_without_a_language_uses_default_lang(tmp_path, practice):
    response = post(tmp_path, practice, ATTEMPTS, {"slug": "two-sum"})
    assert response.json()["language"] == practice.config.default_lang.value


def test_a_start_resumes_the_attempt_in_progress(tmp_path, practice, python_attempt):
    response = post(tmp_path, practice, ATTEMPTS, {"slug": "two-sum", "language": "python"})
    assert response.json()["attempt_id"] == python_attempt.id


def test_a_fresh_start_replaces_the_attempt_in_progress(tmp_path, practice, python_attempt):
    body = {"slug": "two-sum", "language": "python", "fresh": True}
    response = post(tmp_path, practice, ATTEMPTS, body)
    assert response.json()["attempt_id"] != python_attempt.id


def test_a_time_box_is_set_in_minutes(tmp_path, practice):
    body = {"slug": "two-sum", "language": "python", "timer_minutes": 25}
    response = post(tmp_path, practice, ATTEMPTS, body)
    assert in_progress(practice, "two-sum", Language.PYTHON).time_limit_s == 25 * 60
    assert response.json()["timer"] is not None


@pytest.mark.parametrize("minutes", [0, 601, 2.5, "25m", True])
def test_a_time_box_outside_1_to_600_minutes_gets_422(tmp_path, practice, minutes):
    body = {"slug": "two-sum", "language": "python", "timer_minutes": minutes}
    assert error(post(tmp_path, practice, ATTEMPTS, body)) == (422, "usage")


def test_a_start_of_an_item_takes_no_language(tmp_path, practice):
    response = post(tmp_path, practice, ATTEMPTS, {"slug": "url-shortener"})
    assert (response.status_code, response.json()["kind"]) == (201, "item")


def test_an_item_with_a_language_gets_the_clis_refusal(tmp_path, practice):
    response = post(tmp_path, practice, ATTEMPTS, {"slug": "url-shortener", "language": "python"})
    assert (error(response), message(response)) == (
        (422, "usage"),
        "url-shortener is not autograded; --lang applies to problems",
    )


def test_a_project_starts_in_its_language(tmp_path, project):
    response = post(tmp_path, project, ATTEMPTS, {"slug": PROJECT_SLUG})
    assert (response.status_code, response.json()["language"]) == (201, "python")


def test_an_unknown_problem_gets_404(tmp_path, practice):
    assert error(post(tmp_path, practice, ATTEMPTS, {"slug": "no-such"})) == (404, "not_found")


def test_a_start_without_a_slug_gets_422(tmp_path, practice):
    response = post(tmp_path, practice, ATTEMPTS, {"language": "python"})
    assert (error(response), message(response)) == ((422, "usage"), "the request needs slug")


def test_an_unknown_language_gets_422(tmp_path, practice):
    response = post(tmp_path, practice, ATTEMPTS, {"slug": "two-sum", "language": "cobol"})
    assert error(response) == (422, "usage")


def test_a_body_that_is_not_an_object_gets_422(tmp_path, practice):
    assert error(post(tmp_path, practice, ATTEMPTS, ["two-sum"])) == (422, "usage")


def test_a_start_the_selected_jdk_cannot_run_is_refused_with_the_clis_fix(tmp_path):
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    environment = make_environment(root, jdk=jdk_of(27), toolchains=FakeToolchains())
    response = post(tmp_path, environment, ATTEMPTS, {"slug": "two-sum", "language": "java"})
    assert (response.status_code, response.json()["error"]) == (
        503,
        {
            "code": "environment",
            "message": "two-sum runs its java version on JDK 21 to 26; "
            "JAVA_HOME selects JDK 27, which cstudy does not support yet",
            "fix": JDK_FIX,
        },
    )


# hints


def hints(attempt: Attempt) -> str:
    return f"{ATTEMPTS}/{attempt.id}/hints"


def test_a_hint_answers_its_number_total_and_text(tmp_path, practice, python_attempt):
    response = post(tmp_path, practice, hints(python_attempt))
    assert response.json() == {
        "hint": {
            "number": 1,
            "total": 2,
            "markdown": FIRST_HINT,
            "html": render_markdown(FIRST_HINT),
        }
    }


def test_a_hint_counts_on_the_attempt(tmp_path, practice, python_attempt):
    post(tmp_path, practice, hints(python_attempt))
    assert in_progress(practice, "two-sum", Language.PYTHON).hints_used == 1


def test_no_more_hints_answers_exhausted(tmp_path, practice, python_attempt):
    practice.progress.update_attempt(replace(python_attempt, hints_used=2))
    assert post(tmp_path, practice, hints(python_attempt)).json() == {"exhausted": True}


def test_a_projects_hint_of_a_locked_level_answers_that_level(tmp_path, project):
    attempt = start_attempt(project, StartRequest(PROJECT_SLUG)).attempt
    project.progress.update_attempt(replace(attempt, hints_used=1))
    assert post(tmp_path, project, hints(attempt)).json() == {"locked_until_level": 2}


def test_a_hint_goes_to_the_addressed_attempt(tmp_path, practice, python_attempt):
    start_attempt(practice, StartRequest("two-sum", Language.KOTLIN))
    post(tmp_path, practice, hints(python_attempt))
    used = [in_progress(practice, "two-sum", language).hints_used for language in KOTLIN_AND_PYTHON]
    assert used == [0, 1]


def test_a_hint_during_a_mock_gets_the_lock_message(tmp_path, practice):
    request = StartRequest("lru-cache", Language.PYTHON, fresh=True, timer_s=45 * 60, mock=True)
    attempt = start_attempt(practice, request).attempt
    response = post(tmp_path, practice, hints(attempt))
    assert (error(response), message(response)) == (
        (422, "usage"),
        "cstudy hint is locked during the mock interview (lru-cache; 45:00 left); it unlocks "
        "when the timer ends or every problem is done",
    )


def test_a_hint_on_an_ended_attempt_gets_409(tmp_path, practice, python_attempt):
    practice.progress.update_attempt(replace(python_attempt, status=AttemptStatus.PASSED))
    assert error(post(tmp_path, practice, hints(python_attempt))) == (409, "attempt_ended")


# done


def finish(attempt: Attempt) -> str:
    return f"{ATTEMPTS}/{attempt.id}/done"


@pytest.fixture
def passed(practice, python_attempt) -> Attempt:
    record_full_pass(practice, python_attempt)
    practice.clock.advance(SOLVE_TIME)  # type: ignore[attr-defined]
    return python_attempt


def test_done_answers_what_cstudy_done_prints(tmp_path, practice, passed):
    response = post(tmp_path, practice, finish(passed), {"rating": "ok", "notes": "tidy"})
    assert response.json() == {
        "slug": "two-sum",
        "language": "python",
        "status": "passed",
        "levels_finished": None,
        "solve_s": 1120,
        "rating": "ok",
        "grade": "ok",
        "caps": [],
        "hints_used": 0,
        "next_review": {"due_on": "2026-10-27", "in_days": 3, "ease": 2.5},
    }


def test_done_keeps_the_notes(tmp_path, practice, passed):
    post(tmp_path, practice, finish(passed), {"rating": "ok", "notes": "tidy"})
    assert practice.progress.attempt(passed.id).notes == "tidy"  # type: ignore[union-attr]


def test_done_names_the_caps_that_lowered_the_grade(tmp_path, practice, passed):
    practice.progress.update_attempt(replace(passed, first_pass_at=NOW, hints_used=1))
    response = post(tmp_path, practice, finish(passed), {"rating": "easy"})
    assert (response.json()["grade"], response.json()["caps"]) == ("ok", ["hint"])


def test_gave_up_grades_again(tmp_path, practice, python_attempt):
    response = post(tmp_path, practice, finish(python_attempt), {"gave_up": True})
    document = response.json()
    assert (document["status"], document["rating"], document["grade"]) == ("failed", None, "again")


def test_a_rating_without_a_full_pass_gets_the_clis_refusal(tmp_path, practice, python_attempt):
    response = post(tmp_path, practice, finish(python_attempt), {"rating": "ok"})
    assert (error(response), message(response)) == (
        (422, "usage"),
        "the latest test run did not pass every case; run cstudy test, or finish with --gave-up",
    )


def test_both_a_rating_and_gave_up_get_the_clis_refusal(tmp_path, practice, passed):
    response = post(tmp_path, practice, finish(passed), {"rating": "ok", "gave_up": True})
    assert (error(response), message(response)) == (
        (422, "usage"),
        "finish with either --rating easy|ok|hard or --gave-up",
    )


def test_an_unknown_rating_gets_422(tmp_path, practice, passed):
    assert error(post(tmp_path, practice, finish(passed), {"rating": "great"})) == (422, "usage")


def test_done_finishes_the_addressed_attempt(tmp_path, practice, python_attempt):
    kotlin = start_attempt(practice, StartRequest("two-sum", Language.KOTLIN)).attempt
    post(tmp_path, practice, finish(python_attempt), {"gave_up": True})
    assert practice.progress.attempt(kotlin.id).status is AttemptStatus.IN_PROGRESS  # type: ignore[union-attr]


def test_done_on_an_ended_attempt_gets_409(tmp_path, practice, python_attempt):
    practice.progress.update_attempt(replace(python_attempt, status=AttemptStatus.FAILED))
    response = post(tmp_path, practice, finish(python_attempt), {"gave_up": True})
    assert error(response) == (409, "attempt_ended")


def project_through_level_1(project, mock: bool = False) -> Attempt:
    attempt = start_attempt(project, StartRequest(PROJECT_SLUG, mock=mock)).attempt
    levels = (LevelTally(1, 1, 1, 2, 2), LevelTally(2, 1, 0, 2, 2))
    project.progress.add_submission(
        SubmissionRecord(attempt.id, NOW, "abc", 2, True, levels, Tally(total=4), 300)
    )
    return attempt


def test_a_projects_done_reports_the_levels_it_passed_through(tmp_path, project):
    attempt = project_through_level_1(project)
    document = post(tmp_path, project, finish(attempt), {"rating": "easy"}).json()
    assert (
        document["status"],
        document["levels_finished"],
        document["grade"],
        document["caps"],
    ) == (
        "passed",
        1,
        "easy",
        [],
    )


def test_a_project_mocks_done_reports_the_levels_cap(tmp_path, project):
    attempt = project_through_level_1(project, mock=True)
    document = post(tmp_path, project, finish(attempt), {"rating": "easy"}).json()
    assert (document["status"], document["grade"], document["caps"]) == (
        "failed",
        "hard",
        ["levels"],
    )


def test_an_items_done_takes_a_rating(tmp_path, practice):
    attempt = start_item_attempt(practice, ItemStartRequest("url-shortener")).attempt
    document = post(tmp_path, practice, finish(attempt), {"rating": "hard"}).json()
    assert (document["language"], document["status"], document["grade"]) == (
        None,
        "passed",
        "hard",
    )


def test_a_rust_project_started_from_the_page_joins_rust_analyzers_projects(tmp_path):
    toolchains = FakeToolchains(project_test_generators={Language.RUST: RustTestGenerator()})
    root = repository_root(tmp_path, RUST_PROJECT_PROBLEMS)
    environment = make_environment(root, toolchains=toolchains)
    write_ide_files(root, IdeRequest((Ide.VSCODE,)))
    post(tmp_path, environment, ATTEMPTS, {"slug": "bank-project-rust"})
    settings = json.loads((root / ".vscode" / "settings.json").read_text())
    assert any("bank-project-rust" in path for path in settings["rust-analyzer.linkedProjects"])
