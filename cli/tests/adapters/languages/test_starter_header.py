"""The header at the top of a starter file stays within 100 columns, in every language
(docs/specs/runners.md#stub-generation)."""

from collections.abc import Callable
from dataclasses import replace

import pytest

from coding_study.adapters.languages import go, jvm, python, rust, typescript
from coding_study.domain.problem import ProblemMeta
from tests.stub_contract import STUB_CASES

LIMIT = 100
TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
LONG = replace(
    TWO_SUM,
    title="Longest Substring Without Repeats",
    slug="longest-substring-without-repeats",
)
WORDY = replace(
    TWO_SUM,
    title="A Remarkably Long Problem Title That Goes On And On Past The Edge Of Any Editor Window",
    slug="a-remarkably-long-problem-title-that-goes-on",
)
GENERATORS: dict[str, Callable] = {
    "python": python.create_stub_generator,
    "typescript": typescript.create_stub_generator,
    "go": go.create_stub_generator,
    "rust": rust.create_stub_generator,
    "java": jvm.create_java_stub_generator,
    "kotlin": jvm.create_kotlin_stub_generator,
}
LANGUAGES = pytest.mark.parametrize("language", GENERATORS)
COMMENTED = ("typescript", "go", "rust", "java", "kotlin")


def header(language: str, meta: ProblemMeta) -> list[str]:
    """The stub's lines up to the first blank line or code line after the header."""
    lines = GENERATORS[language]().generate(meta).splitlines()
    if language == "python":
        end = next(index for index, line in enumerate(lines) if line.endswith('"""'))
        return lines[: end + 1]
    comment = []
    for line in lines:
        if not line.startswith("//"):
            break
        comment.append(line)
    return comment


def words(lines: list[str], language: str) -> str:
    """The header's text with the comment markers and the line breaks taken out."""
    text = " ".join(lines).replace('"""', "")
    return (
        " ".join(text.replace("//", " ").split())
        if language != "python"
        else " ".join(text.split())
    )


@LANGUAGES
def test_a_short_header_stays_on_one_line(language):
    lines = header(language, TWO_SUM)
    assert len(lines) == 1
    assert "Two Sum." in lines[0]
    assert "Statement: .statements/two-sum.md." in lines[0]
    assert "Run: cstudy test two-sum" in lines[0]


@LANGUAGES
def test_a_long_header_wraps_within_100_columns(language):
    lines = header(language, LONG)
    assert max(map(len, lines)) <= LIMIT
    assert len(lines) > 1


@LANGUAGES
def test_a_wrapped_header_keeps_its_three_parts_whole(language):
    text = words(header(language, LONG), language)
    assert text == (
        "Longest Substring Without Repeats. "
        "Statement: .statements/longest-substring-without-repeats.md. "
        "Run: cstudy test longest-substring-without-repeats"
    )


@LANGUAGES
def test_a_wrapped_header_breaks_between_the_sentences(language):
    lines = [line.removesuffix('"""') for line in header(language, LONG)]
    statement = "Statement: .statements/longest-substring-without-repeats.md."
    command = "Run: cstudy test longest-substring-without-repeats"
    assert any(line.endswith(statement) for line in lines)
    assert any(line.endswith(command) for line in lines)


@LANGUAGES
def test_a_title_too_long_for_a_line_wraps_by_words(language):
    lines = header(language, WORDY)
    assert max(map(len, lines)) <= LIMIT
    assert words(lines, language).startswith(WORDY.title + ".")
    assert words(lines, language).endswith(
        "Run: cstudy test a-remarkably-long-problem-title-that-goes-on"
    )


@pytest.mark.parametrize("language", COMMENTED)
def test_every_wrapped_line_of_a_commented_header_is_a_line_comment(language):
    assert all(line.startswith("// ") for line in header(language, LONG))


def test_a_wrapped_python_header_is_a_docstring_whose_lines_are_not_indented():
    lines = header("python", LONG)
    assert lines[0].startswith('"""Longest Substring Without Repeats.')
    assert lines[-1].endswith('Run: cstudy test longest-substring-without-repeats"""')
    assert all(not line.startswith(" ") for line in lines)
