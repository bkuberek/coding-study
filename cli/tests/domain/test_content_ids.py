"""Canonical content IDs (docs/specs/compatibility.md#canonical-content-ids)."""

import pytest

from coding_study.domain.content_ids import ContentType, content_id, parse_content_id


def test_the_types_are_problem_guide_path_and_doc():
    assert [content_type.value for content_type in ContentType] == [
        "problem",
        "guide",
        "path",
        "doc",
    ]


@pytest.mark.parametrize("content_type", list(ContentType))
@pytest.mark.parametrize("slug", ["two-sum", "a", "p8-availability", "x1-y2-z3"])
def test_an_id_parses_back_to_its_type_and_slug(content_type, slug):
    assert parse_content_id(content_id(content_type, slug)) == (content_type, slug)


def test_an_id_is_the_type_a_slash_and_the_slug():
    assert content_id(ContentType.PROBLEM, "two-sum") == "problem/two-sum"
    assert content_id(ContentType.DOC, "getting-started") == "doc/getting-started"


def test_a_guide_and_a_path_of_one_slug_are_two_ids():
    assert content_id(ContentType.GUIDE, "hashing") != content_id(ContentType.PATH, "hashing")


@pytest.mark.parametrize(
    "text",
    [
        "",
        "two-sum",
        "problem",
        "problem/",
        "/two-sum",
        "item/two-sum",
        "Problem/two-sum",
        "problem/Two-Sum",
        "problem/two_sum",
        "problem/two--sum",
        "problem/-two-sum",
        "problem/two-sum-",
        "problem/1-two-sum",
        "problem/two-sum/extra",
        "problem/two sum",
        "problem/two-sum\n",
        " problem/two-sum",
    ],
)
def test_text_that_is_not_an_id_raises_value_error(text):
    with pytest.raises(ValueError, match="not a content ID"):
        parse_content_id(text)


def test_the_error_names_the_types_for_an_unknown_one():
    with pytest.raises(ValueError, match="problem, guide, path, doc"):
        parse_content_id("item/two-sum")
