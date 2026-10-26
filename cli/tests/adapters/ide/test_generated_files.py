"""Generated IDE files on disk and their manifest
(docs/specs/installation-and-workspaces.md#ide-files)."""

import json
from pathlib import Path

import pytest

from coding_study.adapters.ide.generated_files import MANIFEST_FILE, FsGeneratedFiles
from coding_study.domain.ide import content_digest

TASKS = ".vscode/tasks.json"


@pytest.fixture
def files(tmp_path: Path) -> FsGeneratedFiles:
    return FsGeneratedFiles(tmp_path)


def test_a_missing_file_has_no_digest(files):
    assert files.digest(TASKS) is None


def test_a_file_has_the_digest_of_its_bytes(files, tmp_path):
    (tmp_path / ".vscode").mkdir()
    (tmp_path / TASKS).write_bytes(b"{}\n")
    assert files.digest(TASKS) == content_digest(b"{}\n")


def test_a_directory_has_no_digest(files, tmp_path):
    (tmp_path / TASKS).mkdir(parents=True)
    assert files.digest(TASKS) is None


def test_write_creates_the_directories(files, tmp_path):
    files.write(".idea/runConfigurations/a.xml", "<a />\n")
    assert (tmp_path / ".idea" / "runConfigurations" / "a.xml").read_text() == "<a />\n"


def test_write_keeps_unix_line_endings(files, tmp_path):
    files.write(TASKS, "{\n}\n")
    assert (tmp_path / TASKS).read_bytes() == b"{\n}\n"


def test_remove_deletes_the_file(files, tmp_path):
    files.write(TASKS, "{}\n")
    files.remove(TASKS)
    assert not (tmp_path / TASKS).exists()


def test_without_a_manifest_nothing_is_recorded(files):
    assert files.manifest() == {}


def test_the_manifest_round_trips(files):
    files.save_manifest({TASKS: "abc"})
    assert files.manifest() == {TASKS: "abc"}


def test_the_manifest_is_sorted_indented_json_with_a_newline(files, tmp_path):
    files.save_manifest({TASKS: "b", ".idea/misc.xml": "a"})
    text = (tmp_path / MANIFEST_FILE).read_text()
    expected = {"format": 1, "files": {".idea/misc.xml": "a", TASKS: "b"}}
    assert text == json.dumps(expected, indent=2) + "\n"


@pytest.mark.parametrize("text", ["not json", "[]", '{"format": 99, "files": {}}'])
def test_an_unreadable_manifest_records_nothing(files, tmp_path, text):
    (tmp_path / ".cs").mkdir()
    (tmp_path / MANIFEST_FILE).write_text(text)
    assert files.manifest() == {}
