"""Target levels on set entries (docs/decisions/0024-level-passes.md#target-levels-in-sets): an
entry may name the level of a progressive or project problem it is done at, `{slug: ..., level: 2}`,
alongside the plain slug, whose target is every level."""

import pytest

from coding_study.domain.attempts import AttemptStatus
from coding_study.domain.errors import ConfigError
from coding_study.domain.problem_sets import ProblemSet, parse_sets, standing_of, target_reached
from coding_study.domain.scheduling import ProblemProgress

LEDGER = "tamper-evident-ledger"
PASSED = frozenset({AttemptStatus.PASSED})


def sets_of(*entries: object) -> tuple[ProblemSet, ...]:
    return parse_sets({"sets": {"loop": {"problems": list(entries)}}})


def issues_of(*entries: object) -> str:
    with pytest.raises(ConfigError) as refused:
        sets_of(*entries)
    return str(refused.value)


# The file


def test_an_entry_may_name_its_target_level():
    assert sets_of({"slug": LEDGER, "level": 2}) == (
        ProblemSet("loop", None, (LEDGER,), ((LEDGER, 2),)),
    )


def test_plain_slugs_and_targets_mix_in_the_set_order():
    found = sets_of("two-sum", {"slug": LEDGER, "level": 2}, "lru-cache")[0]
    assert (found.slugs, found.target_of(LEDGER), found.target_of("two-sum")) == (
        ("two-sum", LEDGER, "lru-cache"),
        2,
        None,
    )


def test_an_entry_without_a_level_targets_every_level():
    assert sets_of({"slug": LEDGER})[0].target_of(LEDGER) is None


@pytest.mark.parametrize("level", [0, -1, "two", True, 1.5])
def test_a_level_must_be_a_whole_number_from_1(level):
    assert f"set loop: the level of {LEDGER} must be a whole number from 1" in issues_of(
        {"slug": LEDGER, "level": level}
    )


def test_an_entry_needs_its_slug():
    assert 'set loop: an entry needs "slug"' in issues_of({"level": 2})


def test_an_entry_names_only_slug_and_level():
    assert 'set loop: unknown key "target"; use slug or level' in issues_of(
        {"slug": LEDGER, "target": 2}
    )


def test_a_slug_listed_twice_in_either_form_is_refused():
    assert f"set loop lists {LEDGER} twice" in issues_of(LEDGER, {"slug": LEDGER, "level": 2})


# Changes keep the targets


SET = ProblemSet("loop", None, ("two-sum", LEDGER, "lru-cache"), ((LEDGER, 2),))


def test_moving_keeps_the_target():
    assert SET.moved(LEDGER, 1) == ProblemSet(
        "loop", None, (LEDGER, "two-sum", "lru-cache"), ((LEDGER, 2),)
    )


def test_taking_an_entry_out_takes_its_target():
    assert SET.without_slugs((LEDGER,)).levels == ()


def test_a_target_can_be_set_and_changed():
    assert SET.with_targets({LEDGER: 3, "two-sum": 1}).levels == (("two-sum", 1), (LEDGER, 3))


# What counts as done


def progress(best: int) -> ProblemProgress:
    return ProblemProgress(PASSED, best_levels=best)


def test_an_entry_with_a_target_is_done_once_a_pass_reached_it():
    assert target_reached(progress(2), 4, 2)


def test_an_entry_below_its_target_is_not_done():
    assert not target_reached(progress(2), 4, 3)


def test_an_entry_without_a_target_needs_every_level():
    assert (target_reached(progress(3), 4, None), target_reached(progress(4), 4, None)) == (
        False,
        True,
    )


def test_a_target_above_the_last_level_needs_the_last():
    assert target_reached(progress(4), 4, 6)


def test_an_entry_without_levels_is_done_once_passed():
    assert (
        target_reached(ProblemProgress(PASSED), None, 2),
        target_reached(ProblemProgress(), None, None),
    ) == (
        True,
        False,
    )


def test_passed_of_total_counts_the_entries_done():
    assert standing_of(SET, ("two-sum", LEDGER, "lru-cache"), {LEDGER}).passed == 1
