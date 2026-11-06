"""The header at the top of a starter file: the title, a short summary of the problem, the
statement's path and the run command, over several lines so that nothing needs horizontal
scrolling, in every language (docs/specs/problem-format.md#starter-header)."""

from collections.abc import Callable
from dataclasses import replace

import pytest

from coding_study.adapters.languages import go, jvm, python, rust, typescript
from coding_study.domain.problem import ProblemMeta
from tests.stub_contract import STUB_CASES

TEXT_WIDTH = 68
SUMMARY = (
    "Given a list of numbers and a target, return the positions of the two numbers "
    "that add up to the target."
)
TWO_SUM = replace(next(case.meta for case in STUB_CASES if case.name == "two-sum"), summary=SUMMARY)
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
TWO_SUM_TEXT = [
    "Two Sum.",
    "",
    "Given a list of numbers and a target, return the positions of the",
    "two numbers that add up to the target.",
    "",
    "Statement: .statements/two-sum.md",
    "Run: cstudy test two-sum",
]


def header(language: str, meta: ProblemMeta) -> list[str]:
    """The stub's lines up to the end of the header comment."""
    lines = GENERATORS[language]().generate(meta).splitlines()
    if language == "python":
        end = next(index for index, line in enumerate(lines) if line.endswith('"""') and index)
        return lines[: end + 1]
    comment = []
    for line in lines:
        if not line.startswith("//"):
            break
        comment.append(line)
    return comment


def text_of(language: str, meta: ProblemMeta) -> list[str]:
    """The header's lines without the comment markers or the docstring's quotes."""
    lines = header(language, meta)
    if language == "python":
        lines[0] = lines[0].removeprefix('"""')
        return [line for line in lines if line != '"""']
    return [line.removeprefix("//").removeprefix(" ") for line in lines]


@LANGUAGES
def test_the_header_reads_title_summary_statement_and_command(language):
    assert text_of(language, TWO_SUM) == TWO_SUM_TEXT


@LANGUAGES
def test_a_header_without_a_summary_has_no_summary_paragraph(language):
    text = text_of(language, replace(TWO_SUM, summary=None))
    assert text == ["Two Sum.", "", "Statement: .statements/two-sum.md", "Run: cstudy test two-sum"]


@LANGUAGES
def test_the_header_text_wraps_within_the_width(language):
    long_summary = replace(TWO_SUM, summary=SUMMARY * 2)
    prose = text_of(language, long_summary)[2:-3]
    assert max(map(len, prose)) <= TEXT_WIDTH


@LANGUAGES
def test_a_long_summary_wraps_over_more_lines(language):
    long_summary = replace(TWO_SUM, summary=SUMMARY * 2)
    assert len(text_of(language, long_summary)) > len(TWO_SUM_TEXT)


@pytest.mark.parametrize("language", COMMENTED)
def test_no_commented_header_line_passes_72_columns(language):
    assert max(map(len, header(language, replace(TWO_SUM, summary=SUMMARY * 2)))) <= 71


@pytest.mark.parametrize("language", COMMENTED)
def test_every_line_of_a_commented_header_is_a_line_comment(language):
    assert all(line.startswith("//") for line in header(language, LONG))


@pytest.mark.parametrize("language", COMMENTED)
def test_a_blank_line_of_a_commented_header_is_a_bare_comment_marker(language):
    assert header(language, TWO_SUM)[1] == "//"


@LANGUAGES
def test_the_statement_path_and_the_command_are_whole_lines(language):
    text = text_of(language, LONG)
    assert text[-2:] == [
        "Statement: .statements/longest-substring-without-repeats.md",
        "Run: cstudy test longest-substring-without-repeats",
    ]


@LANGUAGES
def test_a_title_too_long_for_a_line_wraps_by_words(language):
    text = text_of(language, WORDY)
    title = text[: text.index("")]
    assert max(map(len, title)) <= TEXT_WIDTH
    assert " ".join(title) == WORDY.title + "."


def test_a_python_header_is_a_docstring_whose_lines_are_not_indented():
    lines = header("python", TWO_SUM)
    assert lines[0] == '"""Two Sum.'
    assert lines[-1] == '"""'
    assert all(not line.startswith(" ") for line in lines)


def test_a_python_header_quotes_are_escaped():
    quoted = replace(TWO_SUM, summary='Return the word "yes" or a back\\slash.')
    assert 'Return the word \\"yes\\" or a back\\\\slash.' in header("python", quoted)


def test_a_concurrent_python_header_names_the_model_in_a_paragraph_of_its_own():
    concurrent = next(case.meta for case in STUB_CASES if case.name == "bounded-blocking-queue")
    assert text_of("python", replace(concurrent, summary="Block when full."))[-2:] == [
        "",
        "Concurrency: threads",
    ]


@pytest.mark.parametrize("language", COMMENTED)
def test_a_concurrent_commented_header_names_the_model_after_the_command(language):
    concurrent = next(case.meta for case in STUB_CASES if case.name == "bounded-blocking-queue")
    stub = GENERATORS[language]().generate(replace(concurrent, summary="Block when full."))
    lines = stub.splitlines()
    command = lines.index("// Run: cstudy test bounded-blocking-queue")
    assert lines[command + 1].startswith("// Concurrency: ")
