"""The use cases of `cstudy set` and the Sets view (docs/specs/cli.md#cstudy-set), over a real
`sets.yaml` and a real database."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.problem_sets import (
    add_to_set,
    create_set,
    delete_set,
    find_set,
    move_in_set,
    read_sets,
    remove_from_set,
    rename_set,
    set_standing,
    set_view,
)
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.errors import ConfigError, UnknownSetError, UsageError
from coding_study.domain.problem import Language
from coding_study.domain.problem_sets import ProblemSet
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
LOOP = "backend-loop"


@pytest.fixture
def environment(tmp_path: Path):
    return make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))


@pytest.fixture
def looped(environment):
    create_set(environment, LOOP)
    return environment


def finish(environment, slug: str, status: AttemptStatus = AttemptStatus.PASSED) -> None:
    progress = environment.progress
    attempt = progress.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.NEW, NOW))
    progress.update_attempt(replace(attempt, status=status, ended_at=NOW, grade=Grade.OK))


def test_a_new_set_is_empty(environment):
    assert create_set(environment, LOOP) == ProblemSet(LOOP)


def test_a_new_set_is_in_the_file(looped):
    assert read_sets(looped) == (ProblemSet(LOOP),)


def test_a_description_is_kept_on_one_line(environment):
    assert create_set(environment, LOOP, "on the\n  12th").description == "on the 12th"


def test_creating_a_name_that_exists_is_an_error_not_a_merge(looped):
    add_to_set(looped, LOOP, ("two-sum",))
    with pytest.raises(UsageError, match=f"set {LOOP} already exists"):
        create_set(looped, LOOP)
    assert find_set(looped, LOOP).slugs == ("two-sum",)


def test_a_name_that_is_not_a_slug_is_refused(environment):
    with pytest.raises(UsageError, match='invalid set name "Backend Loop"'):
        create_set(environment, "Backend Loop")


def test_a_refused_name_makes_no_file(tmp_path, environment):
    with pytest.raises(UsageError):
        create_set(environment, "Backend Loop")
    assert not (tmp_path / "sets.yaml").exists()


def test_finding_an_unknown_set_names_yours(looped):
    with pytest.raises(UnknownSetError, match=f'unknown set "nope"; your sets: {LOOP}'):
        find_set(looped, "nope")


def test_finding_a_set_with_none_says_how_to_make_one(environment):
    with pytest.raises(UnknownSetError, match="create it with cstudy set create nope"):
        find_set(environment, "nope")


def test_adding_keeps_the_order_given(looped):
    add_to_set(looped, LOOP, ("lru-cache", "two-sum"))
    assert find_set(looped, LOOP).slugs == ("lru-cache", "two-sum")


def test_adding_says_what_it_added(looped):
    assert add_to_set(looped, LOOP, ("two-sum",)).changed == ("two-sum",)


def test_an_item_can_be_added(looped):
    add_to_set(looped, LOOP, ("url-shortener",))
    assert find_set(looped, LOOP).slugs == ("url-shortener",)


def test_a_problem_can_be_in_two_sets(looped):
    create_set(looped, "data-loop")
    add_to_set(looped, LOOP, ("two-sum",))
    add_to_set(looped, "data-loop", ("two-sum",))
    assert [found.holds("two-sum") for found in read_sets(looped)] == [True, True]


def test_adding_a_slug_already_there_does_nothing_and_says_so(looped):
    add_to_set(looped, LOOP, ("two-sum",))
    change = add_to_set(looped, LOOP, ("two-sum",))
    assert (change.changed, change.unchanged, find_set(looped, LOOP).slugs) == (
        (),
        ("two-sum",),
        ("two-sum",),
    )


def test_a_slug_given_twice_is_added_once(looped):
    add_to_set(looped, LOOP, ("two-sum", "two-sum"))
    assert find_set(looped, LOOP).slugs == ("two-sum",)


def test_adding_nothing_new_leaves_the_file_alone(tmp_path, looped):
    add_to_set(looped, LOOP, ("two-sum",))
    file = tmp_path / "sets.yaml"
    before = file.stat().st_mtime_ns
    add_to_set(looped, LOOP, ("two-sum",))
    assert file.stat().st_mtime_ns == before


def test_a_slug_in_no_catalog_is_refused_with_a_suggestion(looped):
    with pytest.raises(UsageError, match=r'unknown problem "two-summ"; did you mean two-sum\?'):
        add_to_set(looped, LOOP, ("two-summ",))


def test_one_unknown_slug_refuses_them_all(looped):
    with pytest.raises(UsageError):
        add_to_set(looped, LOOP, ("two-sum", "nope"))
    assert find_set(looped, LOOP).slugs == ()


def test_adding_to_an_unknown_set_is_refused(environment):
    with pytest.raises(UnknownSetError):
        add_to_set(environment, LOOP, ("two-sum",))


def test_removing_says_what_it_removed(looped):
    add_to_set(looped, LOOP, ("two-sum", "lru-cache"))
    assert remove_from_set(looped, LOOP, ("two-sum",)).changed == ("two-sum",)


def test_removing_keeps_the_others(looped):
    add_to_set(looped, LOOP, ("two-sum", "lru-cache"))
    remove_from_set(looped, LOOP, ("two-sum",))
    assert find_set(looped, LOOP).slugs == ("lru-cache",)


def test_removing_a_slug_not_there_does_nothing_and_says_so(looped):
    assert remove_from_set(looped, LOOP, ("two-sum",)).unchanged == ("two-sum",)


def test_a_slug_the_catalog_lost_can_be_removed(tmp_path, looped):
    (tmp_path / "sets.yaml").write_text(f"sets:\n  {LOOP}:\n    problems:\n      - gone\n")
    remove_from_set(looped, LOOP, ("gone",))
    assert find_set(looped, LOOP).slugs == ()


def test_moving_changes_the_order(looped):
    add_to_set(looped, LOOP, ("two-sum", "lru-cache", "url-shortener"))
    assert move_in_set(looped, LOOP, "url-shortener", 1).slugs == (
        "url-shortener",
        "two-sum",
        "lru-cache",
    )


def test_moving_is_written(looped):
    add_to_set(looped, LOOP, ("two-sum", "lru-cache"))
    move_in_set(looped, LOOP, "lru-cache", 1)
    assert find_set(looped, LOOP).slugs == ("lru-cache", "two-sum")


def test_moving_outside_the_list_is_refused(looped):
    add_to_set(looped, LOOP, ("two-sum",))
    with pytest.raises(UsageError, match=f"position 2 is outside {LOOP}, which holds 1"):
        move_in_set(looped, LOOP, "two-sum", 2)


def test_renaming_keeps_the_rows(looped):
    add_to_set(looped, LOOP, ("two-sum",))
    rename_set(looped, LOOP, "platform-loop")
    assert read_sets(looped) == (ProblemSet("platform-loop", None, ("two-sum",)),)


def test_renaming_to_a_name_that_exists_is_refused(looped):
    create_set(looped, "data-loop")
    with pytest.raises(UsageError, match="set data-loop already exists"):
        rename_set(looped, LOOP, "data-loop")


def test_renaming_to_a_name_that_is_not_a_slug_is_refused(looped):
    with pytest.raises(UsageError, match="invalid set name"):
        rename_set(looped, LOOP, "Not A Slug")


def test_renaming_an_unknown_set_is_refused(looped):
    with pytest.raises(UnknownSetError):
        rename_set(looped, "nope", "other")


def test_deleting_takes_the_set_out(looped):
    create_set(looped, "data-loop")
    delete_set(looped, LOOP)
    assert [found.name for found in read_sets(looped)] == ["data-loop"]


def test_deleting_an_unknown_set_is_refused(environment):
    with pytest.raises(UnknownSetError):
        delete_set(environment, LOOP)


def test_deleting_leaves_progress_alone(looped):
    add_to_set(looped, LOOP, ("two-sum",))
    finish(looped, "two-sum")
    delete_set(looped, LOOP)
    assert looped.progress.problem_progress()["two-sum"].has_passed


def test_a_file_that_does_not_parse_stops_a_change_and_stays(tmp_path, environment):
    file = tmp_path / "sets.yaml"
    file.write_text("sets: [unclosed\n")
    with pytest.raises(ConfigError):
        create_set(environment, LOOP)
    assert file.read_text() == "sets: [unclosed\n"


def test_a_change_takes_the_lock_of_the_sets(tmp_path, environment):
    create_set(environment, LOOP)
    assert (tmp_path / ".cs" / "sets.lock").exists()


def standing(environment, slugs: tuple[str, ...]):
    return set_standing(environment, ProblemSet(LOOP, None, slugs))


def test_nothing_passed_is_none_of_the_total(environment):
    found = standing(environment, ("two-sum", "lru-cache"))
    assert (found.passed, found.total) == (0, 2)


def test_a_passed_attempt_counts(environment):
    finish(environment, "two-sum")
    assert standing(environment, ("two-sum", "lru-cache")).passed == 1


def test_a_failed_attempt_does_not_count(environment):
    finish(environment, "two-sum", AttemptStatus.FAILED)
    assert standing(environment, ("two-sum",)).passed == 0


def test_a_passed_problem_that_fell_due_still_counts(environment):
    finish(environment, "two-sum")
    state = ReviewState(interval_days=1, reps=1)
    environment.progress.save_schedule_entry(
        ScheduleEntry("two-sum", state, NOW.date(), Grade.OK, NOW)
    )
    assert standing(environment, ("two-sum",)).passed == 1


def test_a_passed_item_counts(environment):
    finish(environment, "url-shortener")
    assert standing(environment, ("url-shortener",)).passed == 1


def test_a_slug_the_catalog_lost_counts_in_no_total(environment):
    found = standing(environment, ("two-sum", "gone"))
    assert (found.total, found.missing) == (1, ("gone",))


def test_a_passed_slug_the_catalog_lost_counts_for_nothing(environment):
    finish(environment, "gone")
    assert standing(environment, ("gone",)).passed == 0


def test_a_set_is_finished_once_all_passed(environment):
    finish(environment, "two-sum")
    assert standing(environment, ("two-sum", "gone")).finished


def test_a_set_with_nothing_to_pass_is_not_finished(environment):
    assert not standing(environment, ()).finished


def test_the_rows_keep_the_set_s_order(looped):
    add_to_set(looped, LOOP, ("url-shortener", "two-sum"))
    assert [row.slug for row in set_view(looped, LOOP).rows] == ["url-shortener", "two-sum"]


def test_the_rows_count_from_one(looped):
    add_to_set(looped, LOOP, ("url-shortener", "two-sum"))
    assert [row.position for row in set_view(looped, LOOP).rows] == [1, 2]


def test_a_row_says_what_cstudy_list_says(looped):
    add_to_set(looped, LOOP, ("two-sum",))
    finish(looped, "two-sum")
    row = set_view(looped, LOOP).rows[0]
    assert row.listed is not None
    assert (row.listed.status.value, row.passed) == ("passed", True)


def test_a_slug_the_catalog_lost_is_a_row_with_nothing_listed(tmp_path, environment):
    (tmp_path / "sets.yaml").write_text(f"sets:\n  {LOOP}:\n    problems:\n      - gone\n")
    row = set_view(environment, LOOP).rows[0]
    assert (row.slug, row.listed, row.passed) == ("gone", None, False)
