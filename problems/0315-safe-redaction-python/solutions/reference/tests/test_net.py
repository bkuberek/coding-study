import pytest

from redaction.net import found_by_patterns
from redaction.spans import Span


@pytest.mark.parametrize(
    "number",
    ["555-123-4567", "(555) 123-4567", "555.123.4567", "5551234567", "+1 555 123 4567", "1-800-555-0199"],
)
def test_a_phone_number_in_any_of_its_forms_is_found_whole(number: str) -> None:
    assert found_by_patterns(f"call {number}.") == [Span(5, 5 + len(number), "PHONE")]


@pytest.mark.parametrize("text", ["order 5551234567890", "on 2027-03-01", "id A5551234567", "12345"])
def test_a_long_digit_run_or_a_date_is_not_a_phone_number(text: str) -> None:
    assert found_by_patterns(text) == []


def test_an_email_ends_before_the_full_stop_that_ends_the_sentence() -> None:
    assert found_by_patterns("mail ana.k+x@mail.example.com.") == [Span(5, 29, "EMAIL")]
