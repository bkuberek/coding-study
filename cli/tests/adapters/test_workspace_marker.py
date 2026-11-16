"""The marker's `languages` key (docs/specs/installation-and-workspaces.md#marker)."""

import tomllib
from pathlib import Path

import pytest

from coding_study.adapters.workspace_marker import (
    MARKER_FILE,
    MarkerError,
    WorkspaceMarker,
    marker_text,
    read_marker,
    record_license,
    write_languages,
)
from coding_study.domain.problem import Language


def write_marker(directory: Path, text: str) -> None:
    (directory / MARKER_FILE).parent.mkdir(parents=True, exist_ok=True)
    (directory / MARKER_FILE).write_text(text, encoding="utf-8")


def with_languages(value: str) -> str:
    return f'schema = 1\ncreated_with = "0.1.0"\nlanguages = {value}\n'


def test_a_marker_without_languages_chose_none(tmp_path):
    write_marker(tmp_path, 'schema = 1\ncreated_with = "0.1.0"\n')
    assert read_marker(tmp_path).languages is None


def test_a_marker_reads_its_languages(tmp_path):
    write_marker(tmp_path, with_languages('["python", "go"]'))
    assert read_marker(tmp_path).languages == (Language.PYTHON, Language.GO)


def test_languages_out_of_order_read_in_workspace_order(tmp_path):
    write_marker(tmp_path, with_languages('["rust", "java", "python"]'))
    assert read_marker(tmp_path).languages == (Language.PYTHON, Language.JAVA, Language.RUST)


def test_an_unknown_language_makes_the_marker_unreadable(tmp_path):
    write_marker(tmp_path, with_languages('["golang"]'))
    with pytest.raises(MarkerError) as caught:
        read_marker(tmp_path)
    assert str(caught.value) == (
        f"{tmp_path / MARKER_FILE}: languages: "
        'unknown language "golang"; use python, typescript, java, kotlin, go or rust'
    )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("[]", "languages: empty"),
        ('["go", "go"]', "languages: go is listed twice"),
        ('"go"', "languages: not a list"),
        ("3", "languages: not a list"),
    ],
)
def test_a_marker_that_no_workspace_has_is_unreadable(tmp_path, value, message):
    write_marker(tmp_path, with_languages(value))
    with pytest.raises(MarkerError, match=message):
        read_marker(tmp_path)


def test_the_marker_text_has_no_languages_key_when_none_were_chosen():
    text = marker_text(WorkspaceMarker(1, "0.1.0"))
    assert "languages" not in tomllib.loads(text)


def test_the_marker_text_lists_the_chosen_languages_after_the_version():
    text = marker_text(WorkspaceMarker(1, "0.1.0", (Language.PYTHON, Language.GO)))
    assert text.endswith('created_with = "0.1.0"\nlanguages = ["python", "go"]\n')


def test_the_marker_text_reads_back(tmp_path):
    marker = WorkspaceMarker(1, "0.1.0", (Language.JAVA, Language.KOTLIN, Language.RUST))
    write_marker(tmp_path, marker_text(marker))
    assert read_marker(tmp_path) == marker


def test_recording_a_license_keeps_the_languages(tmp_path):
    write_marker(tmp_path, marker_text(WorkspaceMarker(1, "0.1.0", (Language.KOTLIN,))))
    record_license(tmp_path, "kotlin-lsp", "Name", "https://example.com/license")
    assert read_marker(tmp_path).languages == (Language.KOTLIN,)


def test_writing_languages_adds_the_key_after_the_version_and_before_a_table(tmp_path):
    write_marker(
        tmp_path,
        'schema = 1\ncreated_with = "0.1.0"\n\n[licenses.kotlin-lsp]\nname = "n"\nurl = "u"\n',
    )
    write_languages(tmp_path, (Language.PYTHON, Language.GO))
    document = tomllib.loads((tmp_path / MARKER_FILE).read_text())
    assert (document["languages"], document["licenses"]["kotlin-lsp"]["name"]) == (
        ["python", "go"],
        "n",
    )


def test_writing_languages_replaces_the_list_in_place_keeping_comments(tmp_path):
    head = '# mine\nschema = 1\ncreated_with = "0.1.0"\n'
    write_marker(tmp_path, f'{head}languages = ["python", "go"]  # two\nextra = 3\n')
    write_languages(tmp_path, (Language.PYTHON,))
    assert (tmp_path / MARKER_FILE).read_text() == (
        f'{head}languages = ["python"]  # two\nextra = 3\n'
    )


def test_written_languages_read_back_in_workspace_order(tmp_path):
    write_marker(tmp_path, 'schema = 1\ncreated_with = "0.1.0"\n')
    write_languages(tmp_path, (Language.JAVA, Language.KOTLIN, Language.RUST))
    assert read_marker(tmp_path).languages == (Language.JAVA, Language.KOTLIN, Language.RUST)


def test_a_marker_that_does_not_parse_is_not_overwritten_by_writing_languages(tmp_path):
    write_marker(tmp_path, "schema = 1\ncreated_with = \n")
    with pytest.raises(MarkerError):
        write_languages(tmp_path, (Language.PYTHON,))
    assert (tmp_path / MARKER_FILE).read_text() == "schema = 1\ncreated_with = \n"
