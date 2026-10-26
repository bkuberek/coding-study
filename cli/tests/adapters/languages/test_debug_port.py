"""A debug agent only starts where nothing listens yet; asking the port first tells the user
before a build, and never connects to it (an IDE could take the probe for its debuggee)."""

import socket
from collections.abc import Iterator

import pytest

from coding_study.adapters.languages.debug_port import require_free_port
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language


@pytest.fixture
def busy_port() -> Iterator[int]:
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        yield listener.getsockname()[1]


@pytest.fixture
def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_a_free_port_is_accepted(free_port):
    require_free_port(DebugSession(Language.PYTHON, free_port))


def test_a_port_in_use_is_an_environment_error_naming_the_port_and_the_option(busy_port):
    with pytest.raises(RunnerStartError) as raised:
        require_free_port(DebugSession(Language.PYTHON, busy_port))
    assert str(raised.value) == (
        f"cannot debug python: port {busy_port} on 127.0.0.1 is already in use; "
        "stop the other debug session or choose another port with --debug-port"
    )


def test_a_port_in_use_is_where_a_connecting_runner_goes(busy_port):
    require_free_port(DebugSession(Language.JAVA, busy_port, connect=True))


def test_asking_leaves_the_port_free_for_the_agent(free_port):
    require_free_port(DebugSession(Language.JAVA, free_port))
    with socket.socket() as agent:
        agent.bind(("127.0.0.1", free_port))
