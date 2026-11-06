"""`cstudy reset` from the terminal (docs/specs/cli.md#cstudy-reset): the preview, the word, and
the refusals, against a scratch workspace with progress in it."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.process_liveness import processes_naming
from coding_study.adapters.run_activity import ProcessRunActivity
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import reset
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment
from tests.helpers import SCHEMAS_DIRECTORY
from tests.stats_fixture import fill_progress

runner = CliRunner()
PRACTICE_FILE = "python/practice/two_sum.py"
ARCHIVED = ".archive/two-sum/1-python/two_sum.py"
RUN_FILE = ".cs/runs/20261106-1/out.json"


@pytest.fixture
def environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "schemas").symlink_to(SCHEMAS_DIRECTORY)
    environment = make_environment(root)
    fill_progress(environment)
    for path in (PRACTICE_FILE, ARCHIVED, RUN_FILE):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("x")
    monkeypatch.setattr(reset, "load_environment", lambda *_: environment)
    return environment


@pytest.fixture
def at_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reset, "_is_terminal", lambda: True)


def attempts(environment) -> int:
    return environment.progress.snapshot().row_counts()["attempts"]


def run(*arguments: str, typed: str | None = None):
    return runner.invoke(cli.app, ["reset", *arguments], input=typed)


def test_the_preview_prints_what_goes_with_its_counts(environment):
    assert "attempts                6" in run().stdout


def test_the_preview_prints_what_stays(environment):
    assert "config.toml" in run().stdout


def test_a_shell_with_no_terminal_is_refused_without_yes(environment):
    result = run()
    assert (result.exit_code, attempts(environment)) == (ExitCode.USAGE_ERROR, 6)


def test_the_refusal_names_yes(environment):
    assert "--yes" in run().output


def test_yes_resets_without_asking(environment):
    result = run("--yes")
    assert (result.exit_code, attempts(environment)) == (ExitCode.SUCCESS, 0)


def test_it_says_what_it_deleted(environment):
    assert "deleted attempts 6" in run("--yes").stdout


def test_at_a_terminal_it_says_it_cannot_be_undone(environment, at_a_terminal):
    assert "This can't be undone." in run(typed="no\n").stdout


def test_at_a_terminal_it_asks_for_the_word(environment, at_a_terminal):
    assert "Type reset to confirm" in run(typed="no\n").stdout


def test_at_a_terminal_the_word_resets(environment, at_a_terminal):
    result = run(typed="reset\n")
    assert (result.exit_code, attempts(environment)) == (ExitCode.SUCCESS, 0)


@pytest.mark.parametrize("typed", ["\n", "yes\n", "RESET\n"])
def test_at_a_terminal_any_other_answer_deletes_nothing(environment, at_a_terminal, typed):
    result = run(typed=typed)
    assert (result.exit_code, attempts(environment)) == (ExitCode.USAGE_ERROR, 6)


def test_the_practice_files_stay_by_default(environment):
    run("--yes")
    assert (environment.root / PRACTICE_FILE).exists()


def test_files_deletes_the_practice_files(environment):
    run("--yes", "--files")
    assert not (environment.root / PRACTICE_FILE).exists()


def test_the_archive_stays_by_default(environment):
    run("--yes", "--files")
    assert (environment.root / ARCHIVED).exists()


def test_archive_deletes_the_archive(environment):
    run("--yes", "--archive")
    assert not (environment.root / ARCHIVED).exists()


def test_a_run_folder_goes(environment):
    run("--yes")
    assert not (environment.root / RUN_FILE).exists()


def test_a_process_running_from_the_runs_folder_refuses_it(environment, monkeypatch):
    monkeypatch.setattr(reset, "ProcessRunActivity", lambda root: Named("a run is in progress"))
    result = run("--yes")
    assert (result.exit_code, attempts(environment)) == (ExitCode.USAGE_ERROR, 6)


class Named:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def active_run(self) -> str | None:
        return self._reason


def test_a_runner_on_this_workspace_is_seen(tmp_path):
    root = tmp_path / "workspace"
    seen: list[tuple[str, ...]] = []

    def naming(*texts: str) -> list[int]:
        seen.append(texts)
        return [77]

    assert ProcessRunActivity(root, naming).active_run() == (
        "a run or a job is in progress (process 77)"
    )
    assert f"{root}/.cs/runs/" in seen[0]


def test_nothing_running_is_quiet(tmp_path):
    assert ProcessRunActivity(tmp_path, lambda *_: []).active_run() is None


def test_a_real_process_that_names_the_text_is_found():
    """The test's own interpreter was started with this file's module name on no command line; a
    child that sleeps with a marker in its arguments is."""
    import subprocess
    import sys

    marker = "cstudy-reset-marker-of-this-test"
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", marker])
    try:
        assert child.pid in processes_naming(marker)
    finally:
        child.kill()
        child.wait()
