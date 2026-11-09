"""What the app may not print while a case runs."""

from coding_study.domain.http_case import OutputCheck, OutputPattern
from coding_study.domain.http_steps import output_failures

JWT_PATTERN = OutputPattern(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.")
TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJsZWFybmVyIn0.c2ln"
VALUES = {"code": "code-123"}


def test_output_that_holds_nothing_forbidden_passes():
    check = OutputCheck((JWT_PATTERN, "{{code}}"))
    assert output_failures(check, "GET /callback 302\n", VALUES) == ()


def test_output_matching_a_pattern_fails_and_shows_the_start_of_the_match():
    (failure,) = output_failures(OutputCheck((JWT_PATTERN,)), f"token: {TOKEN}\n", VALUES)
    assert failure.startswith('app output: printed "eyJhbGciOiJSUzI1NiJ9.eyJ')
    assert failure.endswith(f"which matches {JWT_PATTERN.regex}")


def test_output_holding_a_captured_value_fails():
    assert output_failures(OutputCheck(("{{code}}",)), "exchanging code-123\n", VALUES) == (
        'app output: printed "code-123", which it must not',
    )


def test_a_text_naming_a_value_never_captured_is_passed_over():
    assert output_failures(OutputCheck(("{{state}}",)), "anything", VALUES) == ()


def test_a_plain_text_is_looked_for_as_it_is():
    assert output_failures(OutputCheck(("password=",)), "login password=x", VALUES) == (
        'app output: printed "password=", which it must not',
    )


def test_every_forbidden_thing_found_is_reported():
    check = OutputCheck((JWT_PATTERN, "{{code}}"))
    assert len(output_failures(check, f"{TOKEN} code-123", VALUES)) == 2


def test_a_long_match_is_cut_short_in_the_reason():
    (failure,) = output_failures(OutputCheck((JWT_PATTERN,)), TOKEN + "a" * 500 + ".", VALUES)
    assert len(failure) < 200
