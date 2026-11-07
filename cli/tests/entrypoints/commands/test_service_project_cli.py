"""`cstudy start`, `show`, `test` and `submit` on a service project, through a fake engine."""

import json

import pytest
from typer.testing import CliRunner

from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.sandbox import (
    PYTHON_IMAGE,
    CommandOutcome,
    StackStartError,
    StartupFailure,
)
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import show, start, submit
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import FOLDER, IMAGE, SLUG, make_content, write_problem

runner = CliRunner()


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox()


@pytest.fixture
def environment(tmp_path, monkeypatch, engine):
    root = make_content(tmp_path)
    write_problem(root)
    built = make_environment(root, sandbox=engine)
    monkeypatch.setattr(start, "load_environment", lambda *_: built)
    monkeypatch.setattr(show, "load_catalog_environment", lambda *_: built)
    monkeypatch.setattr(test_command, "load_environment", lambda *_: built)
    monkeypatch.setattr(submit, "load_environment", lambda *_: built)
    return built


def invoke(*arguments: str):
    return runner.invoke(cli.app, list(arguments))


def start_it():
    return invoke("start", SLUG, "--no-open", "--yes")


def test_start_lists_what_the_problem_needs(environment):
    result = start_it()

    assert result.exit_code == ExitCode.SUCCESS
    assert "needs" in result.output
    assert "node:24-slim" in result.output
    assert "about" in result.output


def test_start_copies_the_starter_and_installs(environment, engine):
    start_it()

    assert environment.workspace.exists(f"{FOLDER}/.env")
    assert engine.called("install")


def test_start_starts_nothing_else(environment, engine):
    start_it()

    assert not engine.called("start")


def test_start_names_its_next_step(environment):
    assert "cstudy test" in start_it().output


def test_start_names_no_entry_class_or_generated_tests(environment):
    output = start_it().output

    assert "entry" not in output
    assert "generated" not in output


def test_start_without_docker_exits_4_with_instructions_and_writes_nothing(environment, engine):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    result = start_it()

    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    assert "docs.docker.com" in result.stderr
    assert not environment.workspace.exists(FOLDER)


def test_start_says_it_is_starting_a_stopped_engine(environment, engine):
    engine.engine = EngineState(EngineStatus.STOPPED)

    assert "starting Docker ..." in start_it().output


def test_a_start_that_would_download_without_a_terminal_names_the_flag(environment, engine):
    engine.every_image_present = False

    result = invoke("start", SLUG, "--no-open")

    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "--yes" in result.stderr
    assert not environment.workspace.exists(FOLDER)
    assert not engine.called("pull")


def test_needs_are_shown_before_any_download(environment, engine):
    engine.every_image_present = False

    result = invoke("start", SLUG, "--no-open")

    assert "needs" in result.output


def test_yes_goes_ahead_and_pulls_what_is_missing(environment, engine):
    engine.every_image_present = False

    assert start_it().exit_code == ExitCode.SUCCESS
    assert set(engine.called("pull")) == {IMAGE, PYTHON_IMAGE}


def test_a_failed_install_exits_4_keeps_the_attempt_and_names_the_retry(environment, engine):
    engine.install_outcome = CommandOutcome(1, "network down\n")

    result = start_it()

    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    assert f"cstudy start {SLUG}" in result.stderr
    assert environment.progress.active_attempt(SLUG) is not None


def test_show_lists_the_needs_above_the_statement(environment):
    output = invoke("show", SLUG).output

    assert output.index("needs") < output.index("# Rooms")


def test_show_starts_nothing(environment, engine):
    engine.engine = EngineState(EngineStatus.STOPPED)

    invoke("show", SLUG)

    assert not engine.called("start_engine")


def test_show_of_a_missing_engine_says_what_to_install(environment, engine):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    assert "docs.docker.com" in invoke("show", SLUG).output.replace("\n", "")


def test_test_exits_0_when_the_command_passes(environment, engine):
    start_it()

    assert invoke("test", SLUG).exit_code == ExitCode.SUCCESS


def test_test_exits_1_when_the_command_fails(environment, engine):
    start_it()
    engine.exec_outcome = CommandOutcome(1, "1 failing\n")

    assert invoke("test", SLUG).exit_code == ExitCode.FAILURES


def test_test_reports_the_two_clocks_apart(environment, engine):
    start_it()
    engine.started_at, engine.ready_at = 0.0, 42.0

    output = invoke("test", SLUG).output

    assert "42.0 s, not counted" in output
    assert "commands.test passed in 0.2 s" in output
    assert "total" in output


def test_test_says_when_the_command_ran_out_of_time(environment, engine):
    start_it()
    engine.exec_outcome = CommandOutcome(124, "", timed_out=True)

    output = invoke("test", SLUG).output

    assert "did not finish within 120 s" in output


@pytest.mark.parametrize(
    "failure", [StartupFailure.BOOTSTRAP, StartupFailure.APP_EXITED, StartupFailure.HEALTH_TIMEOUT]
)
def test_your_code_keeping_the_stack_from_ready_exits_2(environment, engine, failure):
    start_it()
    engine.start_error = StackStartError(failure, "it did not start", "the log tail\n")

    result = invoke("test", SLUG)

    assert result.exit_code == ExitCode.USER_CODE_ERROR
    assert "it did not start" in result.output
    assert "the log tail" in result.output


def test_a_stack_that_failed_for_another_reason_exits_4_as_not_your_code(environment, engine):
    start_it()
    engine.start_error = StackStartError(
        StartupFailure.SERVICE, "this says nothing about your code"
    )

    result = invoke("test", SLUG)

    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    assert "says nothing about your code" in result.stderr


@pytest.mark.parametrize(
    "flag",
    [("--debug",), ("--case", "x"), ("--level", "1"), ("--watch",), ("--json",), ("--events",)],
)
def test_the_flags_of_a_native_run_exit_3(environment, flag):
    start_it()

    result = invoke("test", SLUG, *flag)

    assert result.exit_code == ExitCode.USAGE_ERROR
    assert flag[0] in result.stderr


def test_submit_grades_over_http_and_reports_the_two_clocks(environment, engine):
    start_it()

    result = invoke("submit", SLUG)

    assert result.exit_code == ExitCode.SUCCESS, result.stderr
    assert "startup 2.5 s, not counted" in result.stdout
    assert "cstudy.owner_pid" not in result.stdout


def test_submit_json_says_startup_apart_from_the_duration(environment):
    start_it()

    document = json.loads(invoke("submit", SLUG, "--json").stdout)

    assert document["startup_s"] == 2.5
    assert document["duration_s"] < 2.5


def test_a_bank_problem_never_asks_the_engine_anything(tmp_path, monkeypatch, engine):
    built = make_environment(make_content(tmp_path), sandbox=engine)
    monkeypatch.setattr(show, "load_catalog_environment", lambda *_: built)
    slug = built.problems.list_summaries()[0].meta.slug

    invoke("show", slug)

    assert engine.calls == []
