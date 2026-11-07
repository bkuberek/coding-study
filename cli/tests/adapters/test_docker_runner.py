"""`SubprocessDockerRunner`, with stand-in commands: standard input at end of file always, the
environment reduced, output streamed, and a command past its limit killed."""

from pathlib import Path

import pytest

from coding_study.adapters.docker_sandbox import (
    TIMED_OUT_EXIT_CODE,
    SubprocessDockerRunner,
    http_health,
)
from tests.waits import GENEROUS_WAIT_S

SHORT_LIMIT_S = 0.5
"""The limit the runner is asked to enforce: the test is about that limit."""


def script(tmp_path: Path, body: str) -> str:
    path = tmp_path / "stand-in"
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
    return str(path)


def test_a_missing_executable_is_none(tmp_path):
    assert SubprocessDockerRunner().run((str(tmp_path / "absent"),)) is None


def test_standard_input_is_at_end_of_file(tmp_path):
    """An open pipe makes compose hang on its volume question."""
    command = script(tmp_path, 'cat; echo "end of input"')

    result = SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S)

    assert result is not None
    assert result.output == "end of input\n"


def test_standard_output_and_error_are_combined(tmp_path):
    command = script(tmp_path, "echo out; echo err >&2")

    result = SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S)

    assert result is not None
    assert sorted(result.output.splitlines()) == ["err", "out"]


def test_each_line_is_heard_as_it_comes(tmp_path):
    command = script(tmp_path, "echo one; echo two")
    lines: list[str] = []

    SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S, lines.append)

    assert lines == ["one", "two"]


def test_the_exit_code_comes_back(tmp_path):
    result = SubprocessDockerRunner().run((script(tmp_path, "exit 7"),), GENEROUS_WAIT_S)

    assert result is not None
    assert result.exit_code == 7


def test_a_command_past_its_limit_is_killed(tmp_path):
    command = script(tmp_path, "echo started; exec sleep 600")

    result = SubprocessDockerRunner().run((command,), SHORT_LIMIT_S)

    assert result is not None
    assert result.exit_code == TIMED_OUT_EXIT_CODE
    assert result.output == "started\n"


def test_a_token_in_the_shell_does_not_reach_docker(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_API_TOKEN", "leaked")
    command = script(tmp_path, 'echo "[$MY_API_TOKEN]"')

    result = SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S)

    assert result is not None
    assert result.output == "[]\n"


def test_the_engine_docker_should_talk_to_reaches_it(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "unix:///elsewhere")
    command = script(tmp_path, 'echo "$DOCKER_HOST"')

    result = SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S)

    assert result is not None
    assert result.output == "unix:///elsewhere\n"


def test_a_compose_setting_in_the_shell_stays_out(tmp_path, monkeypatch):
    monkeypatch.setenv("COMPOSE_FILE", "/elsewhere.yaml")
    command = script(tmp_path, 'echo "[$COMPOSE_FILE]"')

    result = SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S)

    assert result is not None
    assert result.output == "[]\n"


@pytest.mark.parametrize("value", ["ok"])
def test_nothing_listening_is_not_healthy(value):
    assert value == "ok"
    assert not http_health(1, "/health")
