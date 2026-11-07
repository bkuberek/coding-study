"""`SubprocessDockerRunner`, with stand-in commands: standard input at end of file always, the
environment reduced, output streamed, and a command past its limit killed."""

from pathlib import Path

import pytest

from coding_study.adapters.docker_sandbox import (
    MAX_LINE_CHARACTERS,
    MAX_OUTPUT_BYTES,
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


def test_output_past_the_limit_keeps_its_end(tmp_path):
    lines = MAX_OUTPUT_BYTES // 8
    command = script(tmp_path, f'seq 1 {lines} | sed "s/^/line /"; echo last line')

    result = SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S)

    assert result is not None
    assert len(result.output) <= MAX_OUTPUT_BYTES
    assert result.output.endswith("last line\n")


def test_output_heard_line_by_line_is_still_held_to_the_limit(tmp_path):
    """`cstudy dev` follows an app with no limit on time, so what it hears must not pile up."""
    lines = MAX_OUTPUT_BYTES // 8
    command = script(tmp_path, f'seq 1 {lines} | sed "s/^/line /"')
    heard: list[str] = []

    result = SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S, heard.append)

    assert result is not None
    assert len(heard) == lines
    assert len(result.output) <= MAX_OUTPUT_BYTES


def test_a_line_with_no_newline_is_held_to_its_limit(tmp_path):
    size = MAX_LINE_CHARACTERS * 3
    command = script(tmp_path, f"head -c {size} /dev/zero | tr '\\0' x")
    heard: list[str] = []

    SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S, heard.append)

    assert max(len(line) for line in heard) <= MAX_LINE_CHARACTERS


def test_a_long_line_loses_nothing_on_the_way(tmp_path):
    size = MAX_LINE_CHARACTERS * 3
    command = script(tmp_path, f"head -c {size} /dev/zero | tr '\\0' x")
    heard: list[str] = []

    SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S, heard.append)

    assert sum(len(line) for line in heard) == size


def test_a_last_line_with_no_newline_is_heard(tmp_path):
    heard: list[str] = []

    SubprocessDockerRunner().run(
        (script(tmp_path, "printf partial"),), GENEROUS_WAIT_S, heard.append
    )

    assert heard == ["partial"]


def test_a_carriage_return_ends_a_line_as_a_newline_does(tmp_path):
    heard: list[str] = []

    SubprocessDockerRunner().run(
        (script(tmp_path, r"printf 'one\rtwo\r\nthree\n'"),), GENEROUS_WAIT_S, heard.append
    )

    assert heard == ["one", "two", "three"]


def test_output_that_is_not_utf8_is_replaced_not_refused(tmp_path):
    result = SubprocessDockerRunner().run(
        (script(tmp_path, r"printf 'a\377b\n'"),), GENEROUS_WAIT_S
    )

    assert result is not None
    assert result.output == "a\ufffdb\n"


def test_a_character_split_across_two_writes_stays_whole(tmp_path):
    command = script(tmp_path, r"printf '\303'; sleep 0.2; printf '\251\n'")
    heard: list[str] = []

    result = SubprocessDockerRunner().run((command,), GENEROUS_WAIT_S, heard.append)

    assert result is not None
    assert heard == ["\u00e9"]
    assert result.output == "\u00e9\n"


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
