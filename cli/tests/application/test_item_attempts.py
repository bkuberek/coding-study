import re
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.adapters.fs_study_guides import FsStudyGuides
from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.item_solution import reveal_item_solution
from coding_study.application.practice_catalog import is_item
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, Rating
from coding_study.domain.errors import UsageError
from coding_study.domain.items import GuideLink
from tests.fakes import FakeClock, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
NOTES = "notes/system-design/url-shortener.md"
STATEMENT = ".statements/url-shortener.md"
GUIDE_REFERENCE = "distributed-systems-study-guide.md#databases"
GUIDE_FILE = "distributed-systems-study-guide.md"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def environment(tmp_path, clock):
    return make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS), clock=clock)


@pytest.fixture
def guides_root(tmp_path) -> Path:
    root = tmp_path / "study-guides"
    root.mkdir()
    (root / GUIDE_FILE).write_text("# Distributed systems\n")
    return root


@pytest.fixture
def guided(environment, guides_root):
    return replace(environment, study_guides=FsStudyGuides(guides_root))


def start(environment, slug: str = "url-shortener", **fields):
    return start_item_attempt(environment, ItemStartRequest(slug, **fields))


def finish(environment, rating: Rating = Rating.OK):
    return complete_attempt(environment, DoneRequest(rating=rating))


def test_items_are_recognized(environment):
    assert (is_item(environment, "url-shortener"), is_item(environment, "two-sum")) == (True, False)


def test_start_copies_the_template_to_the_notes(environment):
    start(environment)
    assert "## Data model" in environment.workspace.read_text(NOTES)


def test_notes_begin_with_the_header(environment):
    start(environment)
    assert environment.workspace.read_text(NOTES).startswith("<!-- URL Shortener. Prompt: ")


def test_start_renders_the_prompt(environment):
    start(environment)
    assert "100 redirects for every link created" in environment.workspace.read_text(STATEMENT)


def test_code_review_statement_shows_the_diff(environment):
    start(environment, "retry-wrapper")
    statement = environment.workspace.read_text(".statements/retry-wrapper.md")
    assert "```diff\n--- a/payments/client.py" in statement


def test_start_records_an_attempt_without_a_language(environment):
    attempt = start(environment).attempt
    assert (attempt.language, attempt.status, attempt.stub_path) == (
        None,
        AttemptStatus.IN_PROGRESS,
        NOTES,
    )


def test_start_reports_the_files(environment):
    started = start(environment)
    assert (started.notes_path, started.statement_path, started.created_notes) == (
        NOTES,
        STATEMENT,
        True,
    )


def test_starting_again_resumes(environment):
    first = start(environment)
    again = start(environment)
    assert (again.attempt.id, again.resumed) == (first.attempt.id, True)


def test_resuming_keeps_the_notes(environment):
    start(environment)
    environment.workspace.write_text(NOTES, "my answer\n")
    start(environment)
    assert environment.workspace.read_text(NOTES) == "my answer\n"


def test_fresh_archives_the_notes(environment):
    first = start(environment)
    environment.workspace.write_text(NOTES, "my answer\n")
    archived = start(environment, fresh=True).archived_to
    assert archived == f".archive/url-shortener/{first.attempt.id}-notes/url-shortener.md"


def test_fresh_abandons_the_previous_attempt(environment):
    first = start(environment)
    start(environment, fresh=True)
    assert environment.progress.latest_attempt("url-shortener", None).id != first.attempt.id


def test_review_attempt_archives_the_previous_notes(environment):
    first = start(environment)
    finish(environment)
    review = start(environment)
    assert (review.attempt.mode, review.archived_to) == (
        AttemptMode.REVIEW,
        f".archive/url-shortener/{first.attempt.id}-notes/url-shortener.md",
    )


def test_timer_is_stored(environment):
    assert start(environment, timer_s=2700).attempt.time_limit_s == 2700


def test_done_grades_the_rating(environment):
    start(environment)
    assert finish(environment, Rating.EASY).attempt.grade is Grade.EASY


def test_done_marks_the_item_passed(environment):
    start(environment)
    assert finish(environment).attempt.status is AttemptStatus.PASSED


def test_done_schedules_the_review(environment):
    start(environment)
    assert finish(environment).schedule.state.interval_days == 3


def test_revealing_the_reference_does_not_lower_the_grade(environment):
    start(environment)
    reveal_item_solution(environment, "url-shortener")
    assert finish(environment, Rating.EASY).attempt.grade is Grade.EASY


def test_over_time_does_not_cap_a_self_graded_item(environment, clock):
    start(environment, timer_s=60)
    clock.advance(timedelta(hours=1))
    assert finish(environment, Rating.EASY).attempt.grade is Grade.EASY


def test_giving_up_is_not_allowed_for_items(environment):
    start(environment)
    message = re.escape("self-graded; finish with --rating easy|ok|hard")
    with pytest.raises(UsageError, match=message):
        complete_attempt(environment, DoneRequest(gave_up=True))


def test_solution_shows_the_rubric(environment):
    assert "- [ ] Handles expiry" in (
        reveal_item_solution(environment, "url-shortener").rubric or ""
    )


def test_solution_shows_the_reference(environment):
    view = reveal_item_solution(environment, "url-shortener")
    assert "Pre-generated random keys" in (view.reference or "")


def test_solution_marks_the_attempt_in_progress(environment):
    start(environment)
    reveal_item_solution(environment, "url-shortener")
    assert environment.progress.active_attempt("url-shortener").solution_revealed


def test_start_links_the_located_study_guides(guided, guides_root):
    location = (guides_root / GUIDE_FILE).as_uri()
    assert start(guided).guides == (GuideLink(GUIDE_REFERENCE, location),)


def test_resuming_links_the_located_study_guides(guided):
    start(guided)
    assert len(start(guided).guides) == 1


def test_start_without_a_study_guides_root_links_none(environment):
    assert start(environment).guides == ()


def test_start_skips_a_guide_missing_from_the_root(guided, guides_root):
    (guides_root / GUIDE_FILE).unlink()
    assert start(guided).guides == ()


def test_statement_lists_the_located_study_guides(guided):
    start(guided)
    assert "## Study guides" in guided.workspace.read_text(STATEMENT)
