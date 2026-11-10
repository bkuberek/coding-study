from typing import Any

import pytest

from coding_study.adapters.mock_server.json_values import MISSING, contains, parsed, value_at
from tests.json_subset_table import CONTAINED, NOT_CONTAINED


@pytest.mark.parametrize(("actual", "subset"), CONTAINED)
def test_a_value_contains_its_subset(actual: Any, subset: Any):
    assert contains(actual, subset)


@pytest.mark.parametrize(("actual", "subset"), NOT_CONTAINED)
def test_a_value_does_not_contain_what_differs(actual: Any, subset: Any):
    assert not contains(actual, subset)


def test_a_json_body_parses():
    assert parsed(b'{"stream": true}') == {"stream": True}


def test_a_body_that_is_not_json_is_missing():
    assert parsed(b"{") is MISSING


def test_an_empty_body_is_missing():
    assert parsed(b"") is MISSING


def test_a_body_that_is_not_utf8_is_missing():
    assert parsed(b"\xff") is MISSING


def test_nan_is_not_json():
    assert parsed(b"NaN") is MISSING


def test_a_dotted_path_reads_a_nested_field():
    assert value_at({"usage": {"tokens": 3}}, ("usage", "tokens")) == 3


def test_a_number_in_a_path_reads_a_list_element():
    messages = {"messages": [{"role": "system"}, {"role": "user"}]}
    assert value_at(messages, ("messages", "1", "role")) == "user"


def test_a_path_past_a_list_end_is_missing():
    assert value_at({"messages": []}, ("messages", "0")) is MISSING


def test_a_path_through_a_text_is_missing():
    assert value_at({"model": "m"}, ("model", "name")) is MISSING


def test_an_empty_path_reads_the_whole_value():
    assert value_at([1], ()) == [1]
