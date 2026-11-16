"""`GET` and `POST /api/v1/languages` and `GET /api/v1/languages/removal`: the Settings view's
Profile section, through the use cases of `cstudy lang`
(docs/specs/web-ui.md#session-and-preferences)."""

import os
import stat
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.workspace_marker import read_marker
from coding_study.application.environment import Environment
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.problem import ALL_LANGUAGES, Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.web.runs import Children
from tests.fakes import make_environment
from tests.helpers import SCHEMAS_DIRECTORY
from tests.scripted_runs import QUICK, Script
from tests.web_server import WRITE_HEADERS, session_client, web_app

LANGUAGES = "/api/v1/languages"
REMOVAL = f"{LANGUAGES}/removal"
MARKER = ".cs/workspace.toml"
STAYS = ["progress", ".archive/", "projects/", "notes/"]
RUST_FILES = ("rust/practice/lru_cache.rs", "rust/practice/two_sum.rs")
runner = CliRunner()


def init(target: Path, *arguments: str) -> Path:
    result = runner.invoke(cli.app, ["init", str(target), *arguments])
    assert result.exit_code == 0, result.output
    return target


def workspace(root: Path) -> Environment:
    """The environment over a workspace `cstudy init` made, as the server loads it."""
    (root / "schemas").symlink_to(SCHEMAS_DIRECTORY)
    environment = make_environment(root, workspace_languages=read_marker(root).languages)
    environment.progress.attempts_in_progress()  # creates progress.db, as every command does
    return environment


@pytest.fixture
def everything(tmp_path: Path) -> Environment:
    """A workspace that chose no languages, with IDE files."""
    return workspace(init(tmp_path / "ws"))


@pytest.fixture
def chosen(tmp_path: Path) -> Environment:
    """A workspace of Python and Go, with IDE files."""
    return workspace(init(tmp_path / "ws", "--lang", "python", "--lang", "go"))


def served(tmp_path: Path, environment: Environment, *servers):
    return session_client(web_app(tmp_path / "server", environment, *servers))


def get(tmp_path: Path, environment: Environment, path: str):
    with served(tmp_path, environment) as client:
        return client.get(path)


def post(tmp_path: Path, environment: Environment, body: object):
    with served(tmp_path, environment) as client:
        return client.post(LANGUAGES, json=body, headers=WRITE_HEADERS)


def marker_languages(environment: Environment) -> tuple[Language, ...] | None:
    return read_marker(environment.root).languages


def files_of(root: Path) -> dict[str, bytes]:
    """Every file by path but progress.db, which a command opens and that rows tests count."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink() and not path.name.startswith("progress.db")
    }


def with_rust_files(environment: Environment) -> None:
    for relative in RUST_FILES:
        (environment.root / relative).write_text("mine")


def start_attempt(environment: Environment, language: Language, slug: str = "lru-cache") -> int:
    started = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
    new = NewAttempt(slug, language, AttemptMode.NEW, started)
    return environment.progress.add_attempt(new).id


def error(response) -> tuple[int, str, str]:
    body = response.json()["error"]
    return response.status_code, body["code"], body["message"]


# GET /api/v1/languages


def test_the_languages_are_what_cstudy_lang_list_prints(tmp_path, chosen):
    assert get(tmp_path, chosen, LANGUAGES).json() == {
        "languages": ["python", "go"],
        "chosen": True,
        "folders": ["python/", "go/", "go.work"],
    }


def test_a_workspace_that_chose_none_has_all_six_and_says_so(tmp_path, everything):
    assert get(tmp_path, everything, LANGUAGES).json() == {
        "languages": [language.value for language in ALL_LANGUAGES],
        "chosen": False,
        "folders": ["python/", "typescript/", "jvm/", "go/", "go.work", "rust/"],
    }


def test_listing_the_languages_changes_nothing(tmp_path, chosen):
    before = files_of(chosen.root)
    get(tmp_path, chosen, LANGUAGES)
    assert files_of(chosen.root) == before


# GET /api/v1/languages/removal


def test_the_preview_names_the_folder_and_its_practice_files(tmp_path, everything):
    with_rust_files(everything)
    assert get(tmp_path, everything, f"{REMOVAL}?language=rust").json() == {
        "delete": [{"path": "rust/", "files": 2}],
        "keep": [],
        "stays": STAYS,
        "blocked": [],
    }


def test_the_preview_is_the_preview_cstudy_lang_remove_prints(tmp_path, everything):
    with_rust_files(everything)
    document = get(tmp_path, everything, f"{REMOVAL}?language=rust").json()
    shown = runner.invoke(
        cli.app, ["--workspace", str(everything.root), "lang", "remove", "rust", "--delete-folder"]
    )
    assert shown.stdout.splitlines()[:2] == [
        f"delete     {document['delete'][0]['path']} ({document['delete'][0]['files']} "
        "practice files)",
        f"stays      {', '.join(STAYS[:-1])} and {STAYS[-1]}",
    ]


def test_a_folder_a_remaining_language_uses_stays(tmp_path, everything):
    assert get(tmp_path, everything, f"{REMOVAL}?language=java").json() == {
        "delete": [],
        "keep": [{"path": "jvm/", "reason": "kotlin still uses it"}],
        "stays": STAYS,
        "blocked": [],
    }


def test_both_jvm_languages_delete_the_folder_once(tmp_path, everything):
    query = f"{REMOVAL}?language=java&language=kotlin"
    assert [found["path"] for found in get(tmp_path, everything, query).json()["delete"]] == [
        "jvm/"
    ]


def test_go_and_its_work_file_are_one_entry(tmp_path, everything):
    found = get(tmp_path, everything, f"{REMOVAL}?language=go").json()["delete"]
    assert [entry["path"] for entry in found] == ["go/ and go.work"]


def test_an_attempt_in_progress_blocks_the_deletion_with_the_clis_message(tmp_path, everything):
    attempt = start_attempt(everything, Language.GO)
    blocked = get(tmp_path, everything, f"{REMOVAL}?language=go").json()["blocked"]
    refused = runner.invoke(
        cli.app,
        ["--workspace", str(everything.root), "lang", "remove", "go", "--delete-folder", "--yes"],
    )
    assert (blocked, refused.stderr.strip()) == (
        [refused.stderr.strip().removeprefix("error: ")],
        f"error: cannot delete go/ and go.work: attempt {attempt} (lru-cache, go) is in "
        "progress; finish it with cstudy done or end it with cstudy abort, or remove go "
        "without --delete-folder",
    )


def test_a_folder_that_is_not_there_has_nothing_to_delete(tmp_path, everything):
    rust = everything.root / "rust"
    for path in sorted(rust.rglob("*"), reverse=True):
        path.rmdir() if path.is_dir() else path.unlink()
    rust.rmdir()
    assert get(tmp_path, everything, f"{REMOVAL}?language=rust").json()["delete"] == []


def test_the_preview_changes_nothing(tmp_path, everything):
    with_rust_files(everything)
    before = files_of(everything.root)
    get(tmp_path, everything, f"{REMOVAL}?language=rust")
    assert (files_of(everything.root), marker_languages(everything)) == (before, None)


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("", "the request needs language"),
        ("?language=cobol", 'invalid language "cobol": use one of '),
    ],
)
def test_a_language_the_preview_refuses_gets_422_usage(tmp_path, everything, query, message):
    status, code, text = error(get(tmp_path, everything, f"{REMOVAL}{query}"))
    assert (status, code, text.startswith(message)) == (422, "usage", True)


def test_the_last_language_cannot_be_previewed_for_removal(tmp_path, chosen):
    query = f"{REMOVAL}?language=python&language=go"
    assert error(get(tmp_path, chosen, query)) == (
        422,
        "usage",
        "a workspace needs at least one language",
    )


# POST /api/v1/languages: add and remove, keeping the folders


def test_adding_a_language_writes_its_folder_and_the_marker(tmp_path, chosen):
    response = post(tmp_path, chosen, {"add": ["rust"]})
    document = response.json()
    assert (response.status_code, document["languages"], document["added"]) == (
        200,
        ["python", "go", "rust"],
        ["rust"],
    )
    assert ("rust/Cargo.toml" in document["written"], document["kept"]) == (True, [])
    assert (marker_languages(chosen), (chosen.root / "rust" / "Cargo.toml").is_file()) == (
        (Language.PYTHON, Language.GO, Language.RUST),
        True,
    )


def test_a_change_answers_the_ide_files_it_rewrote(tmp_path, chosen):
    document = post(tmp_path, chosen, {"add": ["rust"]}).json()
    assert ".vscode/launch.json" in document["ide"]


def test_a_change_with_no_ide_files_written_changes_none(tmp_path, chosen):
    for ide in (".vscode", ".idea", ".cs/ide.json"):
        target = chosen.root / ide
        if target.is_dir():
            for path in sorted(target.rglob("*"), reverse=True):
                path.rmdir() if path.is_dir() else path.unlink()
            target.rmdir()
        else:
            target.unlink(missing_ok=True)
    assert post(tmp_path, chosen, {"add": ["rust"]}).json()["ide"] == []


def test_removing_a_language_keeps_its_folder(tmp_path, chosen):
    document = post(tmp_path, chosen, {"remove": ["go"]}).json()
    assert (document["languages"], document["removed"], document["deleted"]) == (
        ["python"],
        ["go"],
        [],
    )
    assert (marker_languages(chosen), (chosen.root / "go").is_dir()) == ((Language.PYTHON,), True)


def test_adds_come_first_so_a_swap_never_leaves_none(tmp_path, chosen):
    document = post(tmp_path, chosen, {"add": ["rust"], "remove": ["python", "go"]}).json()
    assert document["languages"] == ["rust"]


def test_a_workspace_that_chose_none_has_chosen_once_it_changes(tmp_path, everything):
    document = post(tmp_path, everything, {"remove": ["rust"]}).json()
    assert (document["chosen"], document["languages"]) == (
        True,
        ["python", "typescript", "java", "kotlin", "go"],
    )


def test_adding_a_language_a_workspace_has_changes_nothing(tmp_path, everything):
    before = files_of(everything.root)
    document = post(tmp_path, everything, {"add": ["go"]}).json()
    assert (document["added"], document["chosen"], files_of(everything.root)) == (
        [],
        False,
        before,
    )


def test_an_empty_change_answers_the_languages_as_they_are(tmp_path, chosen):
    document = post(tmp_path, chosen, {}).json()
    assert (document["languages"], document["chosen"], document["added"]) == (
        ["python", "go"],
        True,
        [],
    )


def test_a_removal_notes_each_attempt_in_progress_in_a_removed_language(tmp_path, chosen):
    attempt = start_attempt(chosen, Language.GO)
    document = post(tmp_path, chosen, {"remove": ["go"]}).json()
    assert document["notes"] == [f"attempt {attempt} (lru-cache, go) is in progress"]


def test_a_removal_leaves_the_progress_the_archive_and_the_notes_alone(tmp_path, chosen):
    attempt = start_attempt(chosen, Language.GO)
    (chosen.root / ".archive").mkdir()
    (chosen.root / ".archive" / "kept.txt").write_text("mine")
    (chosen.root / "notes" / "mine.md").write_text("mine")
    before = files_of(chosen.root / ".archive"), files_of(chosen.root / "notes")
    post(tmp_path, chosen, {"remove": ["go"]})
    assert (files_of(chosen.root / ".archive"), files_of(chosen.root / "notes")) == before
    assert [found.id for found in chosen.progress.attempts_in_progress()] == [attempt]


# POST: the checks every change makes


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"add": ["go"], "remove": ["go"]}, "cannot add and remove go in one change"),
        ({"add": ["cobol"]}, 'unknown language "cobol"; use python, typescript, java, kotlin'),
        ({"remove": ["python", "go"]}, "a workspace needs at least one language"),
        ({"add": "go"}, 'invalid add "go": use a list of strings'),
        ({"remove": [3]}, "invalid remove [3]: use a list of strings"),
        (
            {"add": ["go"], "delete_folders": "yes"},
            'invalid delete_folders "yes": use true or false',
        ),
    ],
)
def test_a_change_cstudy_lang_refuses_gets_422_and_changes_nothing(tmp_path, chosen, body, message):
    before = files_of(chosen.root)
    status, code, text = error(post(tmp_path, chosen, body))
    assert (status, code, text.startswith(message)) == (422, "usage", True)
    assert files_of(chosen.root) == before


def test_a_body_that_is_not_an_object_gets_422(tmp_path, chosen):
    assert post(tmp_path, chosen, ["rust"]).status_code == 422


def test_a_change_needs_the_csrf_header(tmp_path, chosen):
    with served(tmp_path, chosen) as client:
        response = client.post(LANGUAGES, json={"add": ["rust"]}, headers={})
    assert (response.status_code, marker_languages(chosen)) == (403, (Language.PYTHON, Language.GO))


def test_a_marker_that_does_not_parse_gets_503_and_is_never_overwritten(tmp_path, chosen):
    marker = chosen.root / MARKER
    marker.write_text("schema = 1\ncreated_with = \n")
    response = post(tmp_path, chosen, {"remove": ["go"]})
    assert (response.status_code, response.json()["error"]["code"], marker.read_text()) == (
        503,
        "environment",
        "schema = 1\ncreated_with = \n",
    )


# POST: delete_folders and confirm


def test_a_deletion_without_confirm_asks_the_clis_question_and_changes_nothing(
    tmp_path, everything
):
    with_rust_files(everything)
    before = files_of(everything.root)
    response = post(tmp_path, everything, {"remove": ["rust"], "delete_folders": True})
    assert error(response) == (
        409,
        "confirmation_required",
        "Delete rust/? Its 2 practice files can't be recovered.",
    )
    assert (files_of(everything.root), marker_languages(everything)) == (before, None)


def test_the_question_is_the_one_cstudy_lang_remove_asks(tmp_path, everything):
    asked = runner.invoke(
        cli.app,
        ["--workspace", str(everything.root), "lang", "remove", "go", "--delete-folder"],
        input="n\n",
    )
    question = error(post(tmp_path, everything, {"remove": ["go"], "delete_folders": True}))[2]
    assert question == "Delete go/ and go.work? Its 0 practice files can't be recovered."
    assert asked.exit_code == 3  # no terminal, so it did not ask: the page asks instead


def test_a_confirmed_deletion_deletes_the_folder_and_says_what_went(tmp_path, everything):
    with_rust_files(everything)
    body = {"remove": ["rust"], "delete_folders": True, "confirm": True}
    document = post(tmp_path, everything, body).json()
    assert (document["removed"], document["deleted"]) == (["rust"], [{"path": "rust/", "files": 2}])
    assert ((everything.root / "rust").exists(), (everything.root / "notes").is_dir()) == (
        False,
        True,
    )
    assert marker_languages(everything) == (
        Language.PYTHON,
        Language.TYPESCRIPT,
        Language.JAVA,
        Language.KOTLIN,
        Language.GO,
    )


def test_a_confirmed_deletion_leaves_the_progress_rows_alone(tmp_path, everything):
    attempt = start_attempt(everything, Language.PYTHON)
    body = {"remove": ["rust"], "delete_folders": True, "confirm": True}
    post(tmp_path, everything, body)
    assert [found.id for found in everything.progress.attempts_in_progress()] == [attempt]


def test_a_deletion_with_nothing_to_delete_asks_nothing(tmp_path, everything):
    body = {"remove": ["java"], "delete_folders": True}
    response = post(tmp_path, everything, body)
    assert (response.status_code, response.json()["deleted"]) == (200, [])
    assert (everything.root / "jvm").is_dir()


def test_confirm_alone_deletes_nothing(tmp_path, everything):
    document = post(tmp_path, everything, {"remove": ["rust"], "confirm": True}).json()
    assert (document["deleted"], (everything.root / "rust").is_dir()) == ([], True)


def test_an_attempt_in_progress_refuses_a_deletion_with_the_clis_message(tmp_path, everything):
    attempt = start_attempt(everything, Language.GO)
    before = files_of(everything.root)
    body = {"remove": ["go"], "delete_folders": True, "confirm": True}
    assert error(post(tmp_path, everything, body)) == (
        422,
        "usage",
        f"cannot delete go/ and go.work: attempt {attempt} (lru-cache, go) is in progress; "
        "finish it with cstudy done or end it with cstudy abort, or remove go without "
        "--delete-folder",
    )
    assert (files_of(everything.root), marker_languages(everything)) == (before, None)


def test_a_folder_that_leaves_the_workspace_is_refused_and_stays(tmp_path, everything):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "keep.txt").write_text("outside")
    (everything.root / "rust").rename(tmp_path / "moved-rust")
    (everything.root / "rust").symlink_to(outside, target_is_directory=True)
    body = {"remove": ["rust"], "delete_folders": True, "confirm": True}
    status, code, text = error(post(tmp_path, everything, body))
    assert (status, code, text.startswith("rust leaves the workspace")) == (422, "usage", True)
    assert ((outside / "keep.txt").is_file(), marker_languages(everything)) == (True, None)


@pytest.fixture
def running_job(tmp_path: Path) -> Iterator[tuple[Script, Path]]:
    script = Script(tmp_path / "script.json")
    gate = script.gate("let-it-end")
    script.play({"wait_for": str(gate)}, {"exit": 0})
    yield script, gate
    gate.write_text("")


def start_job(client) -> None:
    body = {"command": "doctor_fix", "confirm": True}
    assert client.post("/api/v1/jobs", json=body, headers=WRITE_HEADERS).status_code == 201


def test_a_job_in_progress_refuses_a_deletion_and_the_preview(tmp_path, everything, running_job):
    script, _ = running_job
    with served(tmp_path, everything, script.child, Children(QUICK)) as client:
        start_job(client)
        body = {"remove": ["rust"], "delete_folders": True, "confirm": True}
        refused = client.post(LANGUAGES, json=body, headers=WRITE_HEADERS)
        previewed = client.get(f"{REMOVAL}?language=rust")
    assert (error(refused)[:2], error(previewed)[:2]) == ((409, "conflict"), (409, "conflict"))
    assert ((everything.root / "rust").is_dir(), marker_languages(everything)) == (True, None)


def test_a_job_in_progress_does_not_hold_back_a_removal_that_keeps_the_folder(
    tmp_path, everything, running_job
):
    script, _ = running_job
    with served(tmp_path, everything, script.child, Children(QUICK)) as client:
        start_job(client)
        response = client.post(LANGUAGES, json={"remove": ["rust"]}, headers=WRITE_HEADERS)
    assert (response.status_code, response.json()["removed"]) == (200, ["rust"])


def test_a_run_a_terminal_started_refuses_a_deletion(tmp_path, everything, monkeypatch):
    from coding_study.entrypoints.web import api_languages

    class Busy:
        def __init__(self, _root: Path) -> None: ...

        def active_run(self) -> str:
            return "a run or a job is in progress (process 4242)"

    monkeypatch.setattr(api_languages, "ProcessRunActivity", Busy)
    body = {"remove": ["rust"], "delete_folders": True, "confirm": True}
    assert error(post(tmp_path, everything, body)) == (
        409,
        "conflict",
        "cstudy lang remove waits until it ends: a run or a job is in progress (process 4242)",
    )


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="needs permissions to deny")
def test_a_folder_that_stays_in_part_answers_503_and_the_marker_still_changes(tmp_path, everything):
    locked = everything.root / "rust" / "practice"
    locked.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        body = {"remove": ["rust"], "delete_folders": True, "confirm": True}
        response = post(tmp_path, everything, body)
    finally:
        locked.chmod(stat.S_IRWXU)
    assert (response.status_code, response.json()["error"]["code"]) == (503, "environment")
    assert Language.RUST not in (marker_languages(everything) or ())
