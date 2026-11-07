"""A problem set and the shape of `sets.yaml` (docs/decisions/0023-problem-sets.md)."""

import pytest

from coding_study.domain.errors import ConfigError, UsageError
from coding_study.domain.problem_sets import (
    ProblemSet,
    one_line,
    parse_sets,
    position_issue,
    set_name_issue,
    unknown_slug_message,
)

BACKEND = ProblemSet("backend-loop", "On the 12th", ("two-sum", "lru-cache", "url-shortener"))


def issues_of(document: object) -> str:
    with pytest.raises(ConfigError) as refused:
        parse_sets(document)
    return str(refused.value)


@pytest.mark.parametrize("name", ["backend-loop", "a", "loop2", "a1-b2-c3", "on", "x" * 64])
def test_a_kebab_case_slug_is_a_name(name):
    assert set_name_issue(name) is None


@pytest.mark.parametrize(
    "name",
    [
        "",
        "Backend",
        "backend loop",
        "-backend",
        "backend-",
        "back--end",
        "2026-loop",
        "a_b",
        "x" * 65,
    ],
)
def test_anything_else_is_not_a_name(name):
    assert set_name_issue(name) is not None


def test_the_refusal_of_a_name_says_what_to_use():
    assert set_name_issue("Backend Loop") == (
        'invalid set name "Backend Loop": use lowercase letters, digits and hyphens, starting with '
        "a letter, at most 64 characters, such as backend-loop"
    )


def test_nothing_is_no_sets():
    assert parse_sets(None) == ()


def test_an_empty_sets_key_is_no_sets():
    assert parse_sets({"sets": None}) == ()


def test_a_set_reads_its_name_description_and_order():
    document = {"sets": {"backend-loop": {"description": "x", "problems": ["b", "a"]}}}
    assert parse_sets(document) == (ProblemSet("backend-loop", "x", ("b", "a")),)


def test_the_sets_keep_the_order_of_the_file():
    document = {"sets": {"zeta": {"problems": []}, "alpha": {"problems": []}}}
    assert [problem_set.name for problem_set in parse_sets(document)] == ["zeta", "alpha"]


def test_a_set_with_no_problems_key_is_empty():
    assert parse_sets({"sets": {"loop": {}}}) == (ProblemSet("loop"),)


def test_a_set_with_nothing_under_it_is_empty():
    assert parse_sets({"sets": {"loop": None}}) == (ProblemSet("loop"),)


@pytest.mark.parametrize(
    ("document", "named"),
    [
        (["a", "b"], "a mapping"),
        ({"set": {}}, 'unknown key "set"'),
        ({"sets": ["a"]}, "sets"),
        ({"sets": {"Bad Name": {}}}, '"Bad Name"'),
        ({"sets": {True: {}}}, "quote"),
        ({"sets": {"loop": ["a"]}}, "loop"),
        ({"sets": {"loop": {"problem": []}}}, 'unknown key "problem"'),
        ({"sets": {"loop": {"problems": "two-sum"}}}, "a list"),
        ({"sets": {"loop": {"problems": [1]}}}, "a slug"),
        ({"sets": {"loop": {"problems": [""]}}}, "a slug"),
        ({"sets": {"loop": {"problems": ["a", "a"]}}}, "twice"),
        ({"sets": {"loop": {"description": 2026}}}, "description"),
    ],
)
def test_a_document_of_another_shape_is_refused_saying_what_is_wrong(document, named):
    assert named in issues_of(document)


def test_a_refusal_names_the_file():
    assert issues_of({"sets": {"loop": []}}).startswith("sets.yaml: ")


def test_every_issue_of_a_file_is_named_at_once():
    document = {"sets": {"Bad": {}, "worse": {"problem": []}}}
    assert ('"Bad"' in issues_of(document), '"problem"' in issues_of(document)) == (True, True)


def test_added_slugs_go_at_the_end_in_the_order_given():
    assert BACKEND.with_slugs(("a", "b")).slugs[-2:] == ("a", "b")


def test_a_set_knows_a_slug_it_holds():
    assert (BACKEND.holds("two-sum"), BACKEND.holds("a")) == (True, False)


def test_taking_out_keeps_the_order_of_the_others():
    assert BACKEND.without_slugs(("lru-cache",)).slugs == ("two-sum", "url-shortener")


def test_moving_to_the_front():
    assert BACKEND.moved("url-shortener", 1).slugs == ("url-shortener", "two-sum", "lru-cache")


def test_moving_to_the_end():
    assert BACKEND.moved("two-sum", 3).slugs == ("lru-cache", "url-shortener", "two-sum")


def test_moving_to_where_it_is_changes_nothing():
    assert BACKEND.moved("lru-cache", 2) == BACKEND


def test_moving_a_slug_it_does_not_hold_is_refused():
    with pytest.raises(UsageError, match="a is not in backend-loop"):
        BACKEND.moved("a", 1)


@pytest.mark.parametrize("position", [0, -1, 4])
def test_a_position_outside_the_list_is_refused(position):
    assert position_issue(BACKEND, position) == (
        f"position {position} is outside backend-loop, which holds 3"
    )


@pytest.mark.parametrize("position", [1, 3])
def test_a_position_at_either_end_is_inside(position):
    assert position_issue(BACKEND, position) is None


def test_moving_outside_the_list_is_refused():
    with pytest.raises(UsageError, match="outside backend-loop"):
        BACKEND.moved("two-sum", 4)


def test_an_unknown_slug_suggests_the_nearest():
    message = unknown_slug_message("two-summ", ("two-sum", "lru-cache"))
    assert message == 'unknown problem "two-summ"; did you mean two-sum?'


def test_several_near_slugs_are_all_suggested():
    message = unknown_slug_message("two-sun", ("two-sum", "two-sums", "lru-cache"))
    assert "two-sum, two-sums" in message or "two-sums, two-sum" in message


def test_with_none_near_it_says_where_to_look():
    message = unknown_slug_message("quantum", ("two-sum",))
    assert message == 'unknown problem "quantum"; see cstudy list'


def test_a_description_is_one_line():
    assert one_line("  the loop\n on   the 12th ") == "the loop on the 12th"


def test_a_blank_description_is_none():
    assert one_line("   ") is None


def test_no_description_is_none():
    assert one_line(None) is None
