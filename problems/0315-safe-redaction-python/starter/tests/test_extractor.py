"""What the extractor gets wrong, in tests. Yours to read, edit and extend."""

from redaction.extractor import propose
from redaction.models import Proposal


def test_a_proposal_in_plain_text_points_at_its_quote() -> None:
    text = "Write to ana@example.com today."

    (email,) = propose(text)

    assert text[email.start : email.end] == email.quote == "ana@example.com"


def test_after_a_non_ascii_character_the_offsets_are_in_bytes_and_point_too_far() -> None:
    text = "Café ana@example.com"

    (email,) = propose(text)

    assert (email.start, email.end) == (6, 21)
    assert text[email.start : email.end] != email.quote


def test_a_name_with_a_last_name_is_proposed_twice() -> None:
    assert propose("Grace Hopper") == [
        Proposal(0, 12, "PERSON", "Grace Hopper"),
        Proposal(6, 12, "PERSON", "Hopper"),
    ]


def test_a_phone_number_in_dots_is_missed() -> None:
    assert propose("call 555.123.4567") == []
