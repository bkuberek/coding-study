"""`cstudy lang` (docs/specs/cli.md#cstudy-lang): list, add and remove the workspace's languages."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode

runner = CliRunner()
MARKER = ".cs/workspace.toml"
TASKS = ".vscode/tasks.json"
TYPECHECK = "cstudy test --typecheck"


def init(target: Path, *arguments: str) -> Path:
    result = runner.invoke(cli.app, ["init", str(target), *arguments])
    assert result.exit_code == 0, result.output
    return target


def lang(workspace: Path, *arguments: str):
    return runner.invoke(cli.app, ["--workspace", str(workspace), "lang", *arguments])


def languages(workspace: Path) -> list[str] | None:
    return tomllib.loads((workspace / MARKER).read_text()).get("languages")


def lines(result) -> list[str]:
    return result.stdout.splitlines()


@pytest.fixture
def everything(tmp_path: Path) -> Path:
    """A workspace that chose no languages, with IDE files."""
    return init(tmp_path / "ws")


@pytest.fixture
def chosen(tmp_path: Path) -> Path:
    """A workspace of Python and Go, with IDE files."""
    return init(tmp_path / "ws", "--lang", "python", "--lang", "go")


def start_attempt(workspace: Path, language: Language, slug: str = "lru-cache") -> int:
    store = SqliteProgressStore(workspace / "progress.db")
    started = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
    return store.add_attempt(NewAttempt(slug, language, AttemptMode.NEW, started)).id


def test_list_names_the_languages_and_their_folders(chosen):
    result = lang(chosen, "list")
    assert (result.exit_code, lines(result)) == (
        0,
        [
            "languages  python, go",
            "folders    python/, go/ and go.work",
            "add        cstudy lang add <language>",
        ],
    )


def test_list_says_when_no_language_was_chosen(everything):
    assert lines(lang(everything, "list"))[0] == (
        "languages  all six (none chosen; cstudy lang remove narrows them)"
    )


def test_list_names_every_folder_of_a_workspace_that_chose_none(everything):
    assert lines(lang(everything, "list"))[1] == (
        "folders    python/, typescript/, jvm/, go/, go.work and rust/"
    )


def test_list_offers_nothing_to_add_to_a_workspace_with_all_six(everything):
    assert "add " not in lang(everything, "list").stdout


def test_list_changes_nothing(chosen):
    before = (chosen / MARKER).read_bytes()
    lang(chosen, "list")
    assert (chosen / MARKER).read_bytes() == before


def test_every_subcommand_needs_a_workspace(tmp_path):
    result = runner.invoke(cli.app, ["--workspace", str(tmp_path), "lang", "list"])
    assert (result.exit_code, "no coding-study workspace" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_add_says_what_it_added_and_wrote(chosen):
    result = lang(chosen, "add", "rust")
    assert (result.exit_code, lines(result)[:2]) == (
        0,
        ["added      rust", "files      rust/: 4 written, 0 kept"],
    )


def test_add_points_to_doctor_fix_last(chosen):
    assert lines(lang(chosen, "add", "rust"))[-1] == "next       cstudy doctor --fix"


def test_add_writes_the_marker_and_the_folder(chosen):
    lang(chosen, "add", "rust")
    assert (languages(chosen), (chosen / "rust" / "Cargo.toml").is_file()) == (
        ["python", "go", "rust"],
        True,
    )


def test_add_names_the_folders_of_a_language_that_has_two(tmp_path):
    workspace = init(tmp_path / "ws", "--lang", "python")
    assert lines(lang(workspace, "add", "go"))[1] == "files      go/ and go.work: 3 written, 0 kept"


def test_add_takes_several_languages_in_workspace_order(tmp_path):
    workspace = init(tmp_path / "ws", "--lang", "python")
    lang(workspace, "add", "rust", "typescript")
    assert languages(workspace) == ["python", "typescript", "rust"]


def test_add_of_a_language_that_is_there_changes_nothing(chosen):
    before = (chosen / MARKER).read_bytes()
    result = lang(chosen, "add", "go")
    assert (result.exit_code, lines(result), (chosen / MARKER).read_bytes()) == (
        0,
        ["go is already one of this workspace's languages"],
        before,
    )


def test_add_to_a_workspace_that_chose_none_says_it_has_all_six(everything):
    assert lines(lang(everything, "add", "go")) == [
        "go is already one of this workspace's languages (it has all six)"
    ]


def test_add_never_overwrites_a_file_of_the_folder(tmp_path):
    workspace = init(tmp_path / "ws", "--lang", "python")
    (workspace / "go").mkdir()
    (workspace / "go" / "go.mod").write_text("module mine\n")
    result = lang(workspace, "add", "go")
    assert (lines(result)[1], (workspace / "go" / "go.mod").read_text()) == (
        "files      go/ and go.work: 2 written, 1 kept",
        "module mine\n",
    )


def test_add_refreshes_the_ide_files_it_wrote(tmp_path):
    workspace = init(tmp_path / "ws", "--lang", "python")
    result = lang(workspace, "add", "typescript")
    assert (
        any(line.startswith("ide        vscode, idea") for line in lines(result)),
        TYPECHECK in (workspace / TASKS).read_text(),
    ) == (True, True)


def test_add_writes_no_ide_file_when_cstudy_wrote_none(tmp_path):
    workspace = init(tmp_path / "ws", "--lang", "python", "--no-ide")
    result = lang(workspace, "add", "typescript")
    assert ("ide " in result.stdout, (workspace / ".vscode").exists()) == (False, False)


def test_an_unknown_language_exits_3_and_changes_nothing(chosen):
    before = (chosen / MARKER).read_bytes()
    result = lang(chosen, "add", "golang")
    assert (result.exit_code, result.stderr.strip(), (chosen / MARKER).read_bytes()) == (
        ExitCode.USAGE_ERROR,
        'error: unknown language "golang"; use python, typescript, java, kotlin, go or rust',
        before,
    )


@pytest.mark.parametrize("subcommand", ["add", "remove"])
def test_a_subcommand_without_a_language_exits_3(chosen, subcommand):
    assert lang(chosen, subcommand).exit_code == ExitCode.USAGE_ERROR


def test_remove_says_what_it_removed_and_kept(chosen):
    result = lang(chosen, "remove", "go")
    assert (result.exit_code, lines(result)[:2]) == (
        0,
        [
            "removed    go",
            "kept       go/ and go.work (cstudy lang remove go --delete-folder deletes it)",
        ],
    )


def test_remove_takes_the_language_out_of_the_marker(chosen):
    lang(chosen, "remove", "go")
    assert languages(chosen) == ["python"]


def test_remove_keeps_the_folder_and_its_practice_files(chosen):
    (chosen / "go" / "practice" / "mine.go").write_text("package practice\n")
    lang(chosen, "remove", "go")
    assert (
        (chosen / "go" / "practice" / "mine.go").read_text(),
        (chosen / "go.work").is_file(),
    ) == ("package practice\n", True)


def test_remove_from_a_workspace_that_chose_none_writes_the_other_five(everything):
    lang(everything, "remove", "rust")
    assert languages(everything) == ["python", "typescript", "java", "kotlin", "go"]


def test_remove_of_java_beside_kotlin_says_nothing_of_the_shared_folder(everything):
    result = lang(everything, "remove", "java")
    assert (lines(result)[0], any(line.startswith("kept") for line in lines(result))) == (
        "removed    java",
        False,
    )


def test_remove_of_both_jvm_languages_keeps_the_one_folder(everything):
    result = lang(everything, "remove", "java", "kotlin")
    assert (
        "kept       jvm/ (cstudy lang remove java kotlin --delete-folder deletes it)"
        in lines(result),
        (everything / "jvm").is_dir(),
    ) == (True, True)


def test_remove_of_a_language_the_workspace_lacks_changes_nothing(chosen):
    before = (chosen / MARKER).read_bytes()
    result = lang(chosen, "remove", "rust")
    assert (result.exit_code, lines(result), (chosen / MARKER).read_bytes()) == (
        0,
        ["rust is not one of this workspace's languages"],
        before,
    )


def test_remove_of_the_last_language_exits_3_and_changes_nothing(tmp_path):
    workspace = init(tmp_path / "ws", "--lang", "python")
    before = (workspace / MARKER).read_bytes()
    result = lang(workspace, "remove", "python")
    assert (result.exit_code, result.stderr.strip(), (workspace / MARKER).read_bytes()) == (
        ExitCode.USAGE_ERROR,
        "error: a workspace needs at least one language",
        before,
    )


def test_remove_of_every_language_exits_3(everything):
    result = lang(everything, "remove", "python", "typescript", "java", "kotlin", "go", "rust")
    assert (result.exit_code, languages(everything)) == (ExitCode.USAGE_ERROR, None)


def test_remove_notes_an_attempt_in_progress(chosen):
    attempt = start_attempt(chosen, Language.GO)
    assert f"note       attempt {attempt} (lru-cache, go) is in progress" in lines(
        lang(chosen, "remove", "go")
    )


def test_remove_keeps_the_attempt_and_progress(chosen):
    attempt = start_attempt(chosen, Language.GO)
    lang(chosen, "remove", "go")
    store = SqliteProgressStore(chosen / "progress.db")
    assert [found.id for found in store.attempts_in_progress()] == [attempt]


def test_remove_says_nothing_of_an_attempt_in_a_language_that_stays(chosen):
    start_attempt(chosen, Language.PYTHON)
    assert "note" not in lang(chosen, "remove", "go").stdout


def test_remove_refreshes_the_ide_files_it_wrote(everything):
    assert TYPECHECK in (everything / TASKS).read_text()
    result = lang(everything, "remove", "typescript")
    assert (
        any(line.startswith("ide        vscode, idea") for line in lines(result)),
        TYPECHECK in (everything / TASKS).read_text(),
    ) == (True, False)


def test_remove_writes_no_ide_file_when_cstudy_wrote_none(tmp_path):
    workspace = init(tmp_path / "ws", "--no-ide")
    result = lang(workspace, "remove", "typescript")
    assert ("ide " in result.stdout, (workspace / ".vscode").exists()) == (False, False)


def test_a_marker_that_does_not_parse_is_never_overwritten(chosen):
    (chosen / MARKER).write_text("schema = 1\ncreated_with = \n")
    result = lang(chosen, "add", "rust")
    assert (result.exit_code, (chosen / MARKER).read_text()) == (
        ExitCode.USAGE_ERROR,
        "schema = 1\ncreated_with = \n",
    )
