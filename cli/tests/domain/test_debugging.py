import pytest

from coding_study.domain.debugging import DebugRequest, DebugSession, debug_session
from coding_study.domain.problem import Language

DEFAULT_PORTS = {
    Language.PYTHON: 5678,
    Language.TYPESCRIPT: 9229,
    Language.JAVA: 5005,
    Language.KOTLIN: 5005,
}


@pytest.mark.parametrize(("language", "port"), DEFAULT_PORTS.items())
def test_each_language_has_its_debug_agents_default_port(language, port):
    assert debug_session(DebugRequest(), language).port == port


def test_an_explicit_port_replaces_the_default():
    assert debug_session(DebugRequest(port=6000), Language.PYTHON).port == 6000


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_the_jvm_can_connect_to_a_debugger_that_is_listening(language):
    assert debug_session(DebugRequest(connect=True), language).connect is True


@pytest.mark.parametrize("language", [Language.PYTHON, Language.TYPESCRIPT])
def test_connecting_is_only_for_the_jvm(language):
    with pytest.raises(ValueError, match="--debug-connect is only for java and kotlin"):
        debug_session(DebugRequest(connect=True), language)


def test_the_session_names_the_loopback_address():
    assert DebugSession(Language.JAVA, 5005).address == "127.0.0.1:5005"


@pytest.mark.parametrize(
    ("language", "port", "line"),
    [
        (Language.PYTHON, 5678, "cstudy: waiting for debugger on 127.0.0.1:5678 (python)"),
        (Language.TYPESCRIPT, 9229, "cstudy: waiting for debugger on 127.0.0.1:9229 (typescript)"),
        (Language.JAVA, 5005, "cstudy: waiting for debugger on 127.0.0.1:5005 (java)"),
        (Language.KOTLIN, 6006, "cstudy: waiting for debugger on 127.0.0.1:6006 (kotlin)"),
    ],
)
def test_ready_line_when_waiting_for_the_ide_to_attach(language, port, line):
    assert DebugSession(language, port).ready_line == line


def test_ready_line_when_connecting_to_a_listening_ide():
    session = DebugSession(Language.KOTLIN, 5005, connect=True)
    assert session.ready_line == "cstudy: connecting to debugger at 127.0.0.1:5005 (kotlin)"
