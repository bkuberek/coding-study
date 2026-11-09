from datetime import date

import pytest

from dates import parse_day


def test_a_real_day_is_that_day():
    assert parse_day("2027-03-01") == date(2027, 3, 1)


def test_a_leap_day_is_real_in_a_leap_year():
    assert parse_day("2028-02-29") == date(2028, 2, 29)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("2027-02-30", id="no such day"),
        pytest.param("2027-02-29", id="no leap day this year"),
        pytest.param("2027-13-01", id="no such month"),
        pytest.param("2027-3-1", id="no zero padding"),
        pytest.param("20270301", id="another ISO form"),
        pytest.param("2027-03-01\n", id="a trailing newline"),
        pytest.param("soon", id="a word"),
    ],
)
def test_names_no_day(text):
    assert parse_day(text) is None
