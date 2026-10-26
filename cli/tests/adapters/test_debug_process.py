from pathlib import Path

import pytest

from coding_study.adapters.debug_process import TAIL_LINES, DebugOutput
from coding_study.application.ports import DebugLaunch
from coding_study.domain.debugging import DebugSession
from coding_study.domain.problem import Language

READY = "agent is listening"
REFUSED = "connect failed"


def output_of(
    tmp_path: Path, *, connect: bool = False, ready: str = READY, refused: str = REFUSED
) -> DebugOutput:
    session = DebugSession(Language.JAVA, 5005, connect)
    debug = DebugLaunch(session, lambda _line: None, ready, refused)
    return DebugOutput(debug, tmp_path / "stdout.txt", tmp_path / "stderr.txt")


def append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(text)


def test_nothing_is_listening_before_the_runner_printed_anything(tmp_path):
    assert output_of(tmp_path).agent_listens() is False


@pytest.mark.parametrize("name", ["stdout.txt", "stderr.txt"])
def test_the_marker_is_found_on_either_stream(tmp_path, name):
    output = output_of(tmp_path)
    append(tmp_path / name, f"banner\n{READY} on 5005\n")
    assert output.agent_listens() is True


def test_a_marker_that_arrives_in_two_pieces_is_found(tmp_path):
    output = output_of(tmp_path)
    append(tmp_path / "stderr.txt", "agent is ")
    assert output.agent_listens() is False
    append(tmp_path / "stderr.txt", "listening\n")
    assert output.agent_listens() is True


def test_a_launch_without_a_ready_marker_never_listens(tmp_path):
    output = output_of(tmp_path, ready="")
    append(tmp_path / "stdout.txt", "anything\n")
    assert output.agent_listens() is False


def test_a_refused_connection_is_recognized_when_connecting(tmp_path):
    output = output_of(tmp_path, connect=True)
    append(tmp_path / "stderr.txt", f"ERROR: {REFUSED}: Connection refused\n")
    assert output.refused_connection() is True


def test_the_refusal_text_means_nothing_when_the_runner_listens(tmp_path):
    output = output_of(tmp_path, connect=False)
    append(tmp_path / "stderr.txt", f"ERROR: {REFUSED}\n")
    assert output.refused_connection() is False


def test_the_tail_has_standard_output_first_then_standard_error(tmp_path):
    output = output_of(tmp_path)
    append(tmp_path / "stdout.txt", "out 1\nout 2\n")
    append(tmp_path / "stderr.txt", "err 1\n")
    assert output.tail() == ("out 1", "out 2", "err 1")


def test_the_tail_keeps_the_last_lines_of_each_stream(tmp_path):
    output = output_of(tmp_path)
    append(tmp_path / "stderr.txt", "".join(f"line {number}\n" for number in range(TAIL_LINES + 5)))
    assert (output.tail()[0], output.tail()[-1], len(output.tail())) == (
        "line 5",
        f"line {TAIL_LINES + 4}",
        TAIL_LINES,
    )
