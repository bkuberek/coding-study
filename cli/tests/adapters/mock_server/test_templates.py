import json
from typing import Any

import pytest

from coding_study.adapters.mock_server.matching import MockRequest
from coding_study.adapters.mock_server.templates import (
    RequestValues,
    has_values,
    rendered_json,
    rendered_text,
)
from tests.mock_template_table import NOT_VALUES, VALUES

CHAT = {
    "model": "chat-small",
    "messages": [
        {"role": "system", "content": "Answer briefly."},
        {"role": "user", "content": "Which desks are free?"},
    ],
    "max_tokens": 64,
    "stream": True,
}


def values(body: Any = CHAT, *, seq: int = 1) -> RequestValues:
    request = MockRequest(
        method="POST",
        path="/v1/chat/completions",
        query={"date": ("2027-03-01", "2027-03-02")},
        headers={"x-request-id": "r-7"},
        body=json.dumps(body).encode() if not isinstance(body, bytes) else body,
    )
    return RequestValues(request, seq)


def test_a_text_echoes_a_field_of_the_request_body():
    assert rendered_text('{"model": "{{request.body.model}}"}', values()) == (
        '{"model": "chat-small"}'
    )


def test_a_number_goes_into_a_text_as_its_json():
    assert rendered_text("max {{request.body.max_tokens}}", values()) == "max 64"


def test_a_missing_field_goes_into_a_text_as_nothing():
    assert rendered_text("[{{request.body.user}}]", values()) == "[]"


def test_a_body_that_is_not_json_has_no_fields():
    assert rendered_text("[{{request.body.model}}]", values(b"model")) == "[]"


def test_a_list_goes_into_a_text_as_compact_json():
    assert rendered_text("{{request.body.messages.0}}", values()) == (
        '{"role":"system","content":"Answer briefly."}'
    )


def test_json_quotes_a_text_for_a_json_document():
    assert rendered_text('{"model": {{json(request.body.model)}}}', values()) == (
        '{"model": "chat-small"}'
    )


def test_json_of_a_missing_field_is_null():
    assert rendered_text("{{json(request.body.user)}}", values()) == "null"


def test_len_counts_a_lists_elements():
    assert rendered_text("{{len(request.body.messages)}}", values()) == "2"


def test_len_counts_a_texts_characters():
    assert rendered_text("{{len(request.body.model)}}", values()) == "10"


def test_len_counts_an_objects_fields():
    assert rendered_text("{{len(request.body)}}", values()) == "4"


def test_len_of_a_missing_field_is_zero():
    assert rendered_text("{{len(request.body.user)}}", values()) == "0"


def test_words_counts_the_words_of_every_text_in_a_value():
    # system, Answer, briefly., user, Which, desks, are, free?
    assert rendered_text("{{words(request.body.messages)}}", values()) == "8"


def test_words_of_a_number_is_zero():
    assert rendered_text("{{words(request.body.max_tokens)}}", values()) == "0"


def test_seq_is_the_requests_number_since_the_last_reset():
    assert rendered_text("chunk-{{seq}}", values(seq=3)) == "chunk-3"


def test_the_method_and_path_are_the_requests():
    assert rendered_text("{{request.method}} {{request.path}}", values()) == (
        "POST /v1/chat/completions"
    )


def test_a_query_key_gives_its_first_value():
    assert rendered_text("{{request.query.date}}", values()) == "2027-03-01"


def test_a_header_is_found_by_its_name_in_any_case():
    assert rendered_text("{{request.headers.X-Request-Id}}", values()) == "r-7"


def test_a_whole_json_string_takes_the_values_own_type():
    template = {"usage": {"prompt_tokens": "{{words(request.body.messages)}}"}}
    assert rendered_json(template, values()) == {"usage": {"prompt_tokens": 8}}


def test_a_whole_json_string_can_hold_a_list():
    assert rendered_json(["{{request.body.messages}}"], values()) == [CHAT["messages"]]


def test_a_whole_json_string_naming_a_missing_field_is_null():
    assert rendered_json({"user": "{{request.body.user}}"}, values()) == {"user": None}


def test_a_json_string_with_more_text_stays_a_string():
    assert rendered_json({"id": "chat-{{seq}}"}, values(seq=2)) == {"id": "chat-2"}


def test_json_keys_are_never_filled_in():
    assert rendered_json({"{{seq}}": 1}, values()) == {"{{seq}}": 1}


@pytest.mark.parametrize("template", VALUES)
def test_a_run_time_value_is_filled_in(template: str):
    assert rendered_text(template, values()) != template


@pytest.mark.parametrize("template", NOT_VALUES)
def test_anything_else_in_braces_is_sent_as_written(template: str):
    assert rendered_text(template, values()) == template


def test_a_text_with_a_value_has_values():
    assert has_values({"a": ["{{seq}}"]})


def test_a_text_with_braces_that_name_no_value_has_none():
    assert not has_values("{{model}}")
