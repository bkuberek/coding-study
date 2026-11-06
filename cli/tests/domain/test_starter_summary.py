"""The summary in a starter's header comes from `meta.yaml`'s `summary`, else from the opening of
the statement (docs/specs/problem-format.md#starter-header)."""

from dataclasses import replace

import pytest

from coding_study.domain.starter_summary import SUMMARY_LIMIT, starter_summary, statement_summary
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")


def problem(statement: str) -> str:
    return f"# Title\n\n## Statement\n\n{statement}\n\n## Input\n\n- `nums`: numbers\n"


def test_the_summary_is_the_opening_of_the_statement():
    text = problem("You get a list of numbers. Find the largest one.")
    assert statement_summary(text) == "You get a list of numbers. Find the largest one."


def test_the_summary_stops_at_the_last_sentence_that_fits_the_cap():
    first = "You get a list of numbers."
    second = "Find the " + "very " * 40 + "largest one."
    assert statement_summary(problem(f"{first} {second}")) == first


def test_the_summary_never_passes_the_cap():
    sentences = " ".join(f"This is sentence number {number} of many." for number in range(30))
    assert len(statement_summary(problem(sentences)) or "") <= SUMMARY_LIMIT


def test_a_first_sentence_over_the_cap_gives_no_summary_rather_than_a_cut_one():
    assert statement_summary(problem("Find " + "a long thing " * 30 + "now.")) is None


def test_only_the_first_paragraph_is_read():
    text = problem("You get a list.\n\nA second paragraph that adds details.")
    assert statement_summary(text) == "You get a list."


def test_a_paragraph_that_introduces_a_list_gives_its_complete_sentences_only():
    text = problem("You get a list. Obey three rules:\n\n- one\n- two")
    assert statement_summary(text) == "You get a list."


def test_a_paragraph_that_only_introduces_a_list_gives_no_summary():
    assert statement_summary(problem("You may trade under three rules:\n\n- one")) is None


def test_a_statement_that_opens_with_a_list_gives_no_summary():
    assert statement_summary(problem("- first\n- second")) is None


def test_a_problem_without_a_statement_section_gives_no_summary():
    assert statement_summary("# Title\n\n## Input\n\nText.\n") is None


@pytest.mark.parametrize(
    ("markdown", "plain"),
    [
        ("Find `nums[i]` now.", "Find nums[i] now."),
        ("A **bold** and *slanted* word.", "A bold and slanted word."),
        ("See [the guide](https://example.test/a) now.", "See the guide now."),
        ("Keep a_b and `x*y` and `p*q` intact.", "Keep a_b and x*y and p*q intact."),
        ("An escaped \\* star.", "An escaped * star."),
        ("A <b>tag</b> goes.", "A tag goes."),
        ("Lines\nwrap   freely.", "Lines wrap freely."),
    ],
)
def test_markdown_is_stripped(markdown, plain):
    assert statement_summary(problem(markdown)) == plain


def test_an_abbreviation_does_not_end_a_sentence():
    text = problem("Pick a value, e.g. the largest one. Then stop.")
    assert statement_summary(text) == "Pick a value, e.g. the largest one. Then stop."


def test_a_question_ends_a_sentence():
    assert statement_summary(problem("Is it sorted? Say so.")) == "Is it sorted? Say so."


def test_a_summary_in_meta_yaml_wins_over_the_statement():
    meta = replace(TWO_SUM, summary="Given   numbers\nand a target, find the pair.")
    assert starter_summary(meta, problem("Some other opening.")) == (
        "Given numbers and a target, find the pair."
    )


def test_without_a_summary_in_meta_yaml_the_statement_gives_it():
    meta = replace(TWO_SUM, summary=None)
    assert starter_summary(meta, problem("Some opening.")) == "Some opening."
