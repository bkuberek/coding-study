from redaction.models import Proposal
from redaction.spans import Span, apply
from redaction.trust import believed, merge, nearest_occurrence


def test_spans_are_applied_by_rebuilding_so_offsets_stay_valid() -> None:
    text = "ab cd ef"

    assert apply(text, [Span(6, 8, "LONGER_LABEL"), Span(0, 2, "X")]) == "[X] cd [LONGER_LABEL]"


def test_a_proposal_that_cuts_out_its_quote_is_believed_as_it_is() -> None:
    assert believed("hi ana", Proposal(3, 6, "PERSON", "ana")) == Span(3, 6, "PERSON")


def test_a_proposal_pointing_too_far_right_is_moved_to_its_quote() -> None:
    assert believed("Café ana", Proposal(6, 9, "PERSON", "ana")) == Span(5, 8, "PERSON")


def test_a_proposal_whose_quote_is_nowhere_or_empty_is_dropped() -> None:
    assert believed("hi ana", Proposal(3, 6, "PERSON", "bob")) is None
    assert believed("hi ana", Proposal(3, 6, "PERSON", "")) is None


def test_the_nearest_occurrence_wins_and_a_tie_goes_to_the_earlier() -> None:
    assert nearest_occurrence("aa-aa", "aa", 3) == 3
    assert nearest_occurrence("aa-aa", "aa", 1) == 0
    assert nearest_occurrence("a.a.a", "a", 3) == 2


def test_touching_spans_stay_apart_and_overlapping_ones_become_one() -> None:
    assert merge([Span(0, 2, "A"), Span(2, 4, "B")]) == [Span(0, 2, "A"), Span(2, 4, "B")]
    assert merge([Span(0, 3, "A"), Span(2, 5, "B"), Span(4, 8, "C")]) == [Span(0, 8, "C")]


def test_a_merged_span_takes_the_label_of_the_longest_then_the_first_started_then_the_first_given() -> None:
    assert merge([Span(2, 4, "A"), Span(0, 5, "B")]) == [Span(0, 5, "B")]
    assert merge([Span(1, 3, "A"), Span(0, 2, "B")]) == [Span(0, 3, "B")]
    assert merge([Span(0, 2, "A"), Span(0, 2, "B")]) == [Span(0, 2, "A")]
