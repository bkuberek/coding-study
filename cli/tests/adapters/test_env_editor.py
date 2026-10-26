from pathlib import Path

from coding_study.adapters.env_editor import NO_EDITOR, EnvEditorOpener

PATHS = (Path("/repo/stub.py"), Path("/repo/statement.md"))


def opener(environ: dict[str, str], commands: list[list[str]]) -> EnvEditorOpener:
    return EnvEditorOpener(environ, commands.append)


def test_runs_visual_with_the_paths():
    commands: list[list[str]] = []
    opener({"VISUAL": "nvim", "EDITOR": "vi"}, commands).open(PATHS)
    assert commands == [["nvim", "/repo/stub.py", "/repo/statement.md"]]


def test_falls_back_to_editor():
    commands: list[list[str]] = []
    opener({"EDITOR": "vi"}, commands).open(PATHS)
    assert commands[0][0] == "vi"


def test_editor_commands_may_carry_arguments():
    commands: list[list[str]] = []
    opener({"VISUAL": "code --wait"}, commands).open(PATHS)
    assert commands[0][:2] == ["code", "--wait"]


def test_reports_success_as_none():
    assert opener({"EDITOR": "vi"}, []).open(PATHS) is None


def test_without_an_editor_says_how_to_set_one():
    assert opener({}, []).open(PATHS) == NO_EDITOR


def test_empty_variables_count_as_unset():
    assert opener({"VISUAL": "", "EDITOR": ""}, []).open(PATHS) == NO_EDITOR


def test_editor_that_cannot_start_is_reported():
    def missing(command: list[str]) -> None:
        raise FileNotFoundError(2, "No such file or directory", command[0])

    result = EnvEditorOpener({"EDITOR": "nope"}, missing).open(PATHS)
    assert result == "cannot run $EDITOR (nope): No such file or directory"
