"""`cstudy lang` (docs/specs/cli.md#cstudy-lang): list, add and remove the workspace's languages."""

import os
import stat
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import lang as lang_command
from coding_study.entrypoints.shared import ExitCode

runner = CliRunner()
MARKER = ".cs/workspace.toml"
TASKS = ".vscode/tasks.json"
TYPECHECK = "cstudy test --typecheck"


def init(target: Path, *arguments: str) -> Path:
    result = runner.invoke(cli.app, ["init", str(target), *arguments])
    assert result.exit_code == 0, result.output
    return target


def lang(workspace: Path, *arguments: str, typed: str | None = None):
    return runner.invoke(cli.app, ["--workspace", str(workspace), "lang", *arguments], input=typed)


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


# `--delete-folder`: docs/specs/cli.md#deleting-a-languages-folder

STAYS = "stays      progress, .archive/, projects/ and notes/"
RUST_FILES = ("rust/practice/lru_cache.rs", "rust/practice/two_sum.rs")
ALL_BUT_RUST = ["python", "typescript", "java", "kotlin", "go"]


@pytest.fixture
def at_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lang_command, "_is_terminal", lambda: True)


class Active:
    def __init__(self, reason: str | None) -> None:
        self._reason = reason

    def active_run(self) -> str | None:
        return self._reason


def with_rust_files(workspace: Path) -> None:
    for relative in RUST_FILES:
        (workspace / relative).write_text("mine")


def files_of(root: Path) -> dict[str, bytes]:
    """Every file by path but progress.db, which a command opens and that rows tests count."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink() and not path.name.startswith("progress.db")
    }


def link_rust_outside(workspace: Path, elsewhere: Path) -> None:
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("outside")
    (workspace / "rust").rename(elsewhere.parent / "moved-rust")
    (workspace / "rust").symlink_to(elsewhere, target_is_directory=True)


def test_the_question_names_the_folder_and_its_practice_files(everything, at_a_terminal):
    with_rust_files(everything)
    result = lang(everything, "remove", "rust", "--delete-folder", typed="y\n")
    assert lines(result)[:3] == [
        "delete     rust/ (2 practice files)",
        STAYS,
        "Delete rust/? Its 2 practice files can't be recovered. [y/N]: y",
    ]


def test_a_yes_removes_the_language_and_deletes_the_folder(everything, at_a_terminal):
    with_rust_files(everything)
    result = lang(everything, "remove", "rust", "--delete-folder", typed="y\n")
    assert (result.exit_code, lines(result)[3:5]) == (
        0,
        ["removed    rust", "deleted    rust/ (2 practice files)"],
    )
    assert (languages(everything), (everything / "rust").exists()) == (ALL_BUT_RUST, False)


def test_a_folder_with_one_practice_file_says_so(everything):
    (everything / RUST_FILES[0]).write_text("mine")
    result = lang(everything, "remove", "rust", "--delete-folder", "--yes")
    assert "delete     rust/ (1 practice file)" in lines(result)


@pytest.mark.parametrize("answer", ["n\n", "\n", "no\n"])
def test_any_answer_but_yes_changes_nothing(everything, at_a_terminal, answer):
    with_rust_files(everything)
    before = files_of(everything)
    result = lang(everything, "remove", "rust", "--delete-folder", typed=answer)
    assert (result.exit_code, lines(result)[-1], files_of(everything)) == (
        0,
        "not removed: nothing changed",
        before,
    )


def test_yes_deletes_without_asking(everything):
    with_rust_files(everything)
    result = lang(everything, "remove", "rust", "--delete-folder", "--yes")
    assert (result.exit_code, "[y/N]" in result.stdout, (everything / "rust").exists()) == (
        0,
        False,
        False,
    )


def test_yes_still_prints_what_goes(everything):
    result = lang(everything, "remove", "rust", "--delete-folder", "--yes")
    assert lines(result)[:2] == ["delete     rust/ (0 practice files)", STAYS]


def test_no_terminal_without_yes_exits_3_after_the_preview_and_changes_nothing(everything):
    before = files_of(everything)
    result = lang(everything, "remove", "rust", "--delete-folder")
    assert (result.exit_code, lines(result)[0], files_of(everything)) == (
        ExitCode.USAGE_ERROR,
        "delete     rust/ (0 practice files)",
        before,
    )
    assert result.stderr.strip() == (
        "error: cstudy lang remove --delete-folder asks before it deletes; in a script, pass --yes"
    )


def test_yes_without_delete_folder_keeps_the_folder(everything):
    result = lang(everything, "remove", "rust", "--yes")
    assert (result.exit_code, (everything / "rust").is_dir(), lines(result)[0]) == (
        0,
        True,
        "removed    rust",
    )


def test_go_is_deleted_with_go_work(everything):
    result = lang(everything, "remove", "go", "--delete-folder", "--yes")
    assert (
        lines(result)[0],
        (everything / "go").exists(),
        (everything / "go.work").exists(),
    ) == ("delete     go/ and go.work (0 practice files)", False, False)


def test_one_jvm_language_leaves_the_folder_the_other_uses(everything):
    result = lang(everything, "remove", "java", "--delete-folder", "--yes")
    assert (lines(result)[:3], (everything / "jvm").is_dir()) == (
        ["keep       jvm/: kotlin still uses it", STAYS, "removed    java"],
        True,
    )


def test_both_jvm_languages_delete_the_folder_once(everything):
    result = lang(everything, "remove", "java", "kotlin", "--delete-folder", "--yes")
    assert (lines(result)[0], (everything / "jvm").exists()) == (
        "delete     jvm/ (0 practice files)",
        False,
    )


def test_several_languages_are_asked_about_once(everything, at_a_terminal):
    result = lang(everything, "remove", "go", "rust", "--delete-folder", typed="y\n")
    assert "Delete go/, go.work and rust/? Their 0 practice files can't be recovered." in (
        result.stdout
    )


def test_a_language_no_longer_listed_has_its_leftover_folder_deleted(chosen):
    (chosen / "rust" / "practice").mkdir(parents=True)
    (chosen / "rust" / "practice" / "two_sum.rs").write_text("mine")
    result = lang(chosen, "remove", "rust", "--delete-folder", "--yes")
    assert (result.exit_code, lines(result)[2:]) == (
        0,
        [
            "rust is not one of this workspace's languages",
            "deleted    rust/ (1 practice file)",
        ],
    )
    assert ((chosen / "rust").exists(), languages(chosen)) == (False, ["python", "go"])


def test_a_folder_that_is_already_gone_asks_nothing(chosen):
    result = lang(chosen, "remove", "rust", "--delete-folder")
    assert (result.exit_code, lines(result)) == (
        0,
        ["rust is not one of this workspace's languages", "rust/ is not there"],
    )


def test_deleting_leaves_progress_and_the_rest_as_they_were(everything):
    attempt = start_attempt(everything, Language.PYTHON, "two-sum")
    kept = (
        ".archive/two-sum/1-rust/two_sum.rs",
        "projects/bank/Cargo.toml",
        "notes/mine.md",
        "problems/my-problem/meta.yaml",
        "sets.yaml",
    )
    for relative in kept:
        (everything / relative).parent.mkdir(parents=True, exist_ok=True)
        (everything / relative).write_text(relative)
    lang(everything, "remove", "rust", "--delete-folder", "--yes")
    store = SqliteProgressStore(everything / "progress.db")
    assert (
        [(everything / relative).read_text() for relative in kept],
        [found.id for found in store.attempts_in_progress()],
    ) == (list(kept), [attempt])


def test_an_attempt_in_progress_refuses_before_the_preview(everything):
    attempt = start_attempt(everything, Language.RUST)
    before = files_of(everything)
    result = lang(everything, "remove", "rust", "--delete-folder", "--yes")
    assert (result.exit_code, result.stdout, files_of(everything)) == (
        ExitCode.USAGE_ERROR,
        "",
        before,
    )
    assert result.stderr.strip() == (
        f"error: cannot delete rust/: attempt {attempt} (lru-cache, rust) is in progress; "
        "finish it with cstudy done or end it with cstudy abort, or remove rust without "
        "--delete-folder"
    )


def test_a_run_or_a_job_refuses_the_deletion(everything, monkeypatch):
    reason = "a run or a job is in progress (process 4242)"
    monkeypatch.setattr(lang_command, "ProcessRunActivity", lambda root: Active(reason))
    before = files_of(everything)
    result = lang(everything, "remove", "rust", "--delete-folder", "--yes")
    assert (result.exit_code, result.stderr.strip(), files_of(everything)) == (
        ExitCode.USAGE_ERROR,
        f"error: cstudy lang remove waits until it ends: {reason}",
        before,
    )


def test_a_run_does_not_stop_a_removal_that_keeps_the_folder(everything, monkeypatch):
    monkeypatch.setattr(lang_command, "ProcessRunActivity", lambda root: Active("a run"))
    assert lang(everything, "remove", "rust").exit_code == 0


def test_a_folder_that_is_a_link_is_refused_and_nothing_is_deleted(everything, tmp_path):
    link_rust_outside(everything, tmp_path / "elsewhere")
    result = lang(everything, "remove", "go", "rust", "--delete-folder", "--yes")
    assert (
        result.exit_code,
        result.stderr.strip(),
        (everything / "go").is_dir(),
        languages(everything),
    ) == (
        ExitCode.USAGE_ERROR,
        "error: rust leaves the workspace, so cstudy lang remove deleted nothing; "
        "remove the link first",
        True,
        None,
    )


def test_removing_the_last_language_exits_3_before_the_preview(tmp_path):
    workspace = init(tmp_path / "ws", "--lang", "go")
    result = lang(workspace, "remove", "go", "--delete-folder", "--yes")
    assert (result.exit_code, result.stdout, (workspace / "go").is_dir()) == (
        ExitCode.USAGE_ERROR,
        "",
        True,
    )


def test_deleting_refreshes_the_ide_files(everything):
    assert TYPECHECK in (everything / TASKS).read_text()
    result = lang(everything, "remove", "typescript", "--delete-folder", "--yes")
    assert (
        any(line.startswith("ide        vscode, idea") for line in lines(result)),
        TYPECHECK in (everything / TASKS).read_text(),
    ) == (True, False)


@pytest.mark.skipif(os.geteuid() == 0, reason="root deletes through a read-only folder")
def test_a_folder_that_stays_in_part_exits_4_and_a_second_run_finishes(everything):
    debug = everything / "rust" / "target" / "debug"
    debug.mkdir(parents=True)
    (debug / "deps").write_text("built")
    debug.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        failed = lang(everything, "remove", "rust", "--delete-folder", "--yes")
        assert (failed.exit_code, languages(everything)) == (
            ExitCode.ENVIRONMENT_ERROR,
            ALL_BUT_RUST,
        )
        assert failed.stderr.strip() == (
            "error: could not delete rust/target/debug/deps: permission denied; "
            "the rest of rust/ is deleted"
        )
    finally:
        debug.chmod(stat.S_IRWXU)
    again = lang(everything, "remove", "rust", "--delete-folder", "--yes")
    assert (again.exit_code, (everything / "rust").exists()) == (0, False)
