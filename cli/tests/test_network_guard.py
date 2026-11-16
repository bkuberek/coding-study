"""The network guard of the fast tests: what it refuses, what it lets through, and who is exempt."""

import socket
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

import pytest

from tests import network_guard

UNROUTABLE = "192.0.2.1"
"""A documentation address (RFC 5737): the guard refuses it before any packet is sent."""


@contextmanager
def refused() -> Iterator[list[str]]:
    """Expect the guard to refuse inside the block, and keep the teardown check from failing."""
    seen: list[str] = []
    try:
        with pytest.raises(network_guard.NetworkRefusedError):
            yield seen
    finally:
        seen.extend(network_guard.disarm())
        network_guard.arm()


def test_a_fast_test_runs_with_the_guard_armed() -> None:
    assert network_guard.is_armed()


def test_a_connect_off_the_loopback_is_refused() -> None:
    with refused() as seen:
        socket.create_connection((UNROUTABLE, 443), timeout=1)
    assert seen
    assert UNROUTABLE in seen[0]


def test_a_name_lookup_is_refused() -> None:
    with refused() as seen:
        socket.getaddrinfo("example.com", 443)
    assert seen
    assert "example.com" in seen[0]


def test_a_numeric_lookup_off_the_loopback_is_refused() -> None:
    with refused():
        socket.getaddrinfo(UNROUTABLE, 443)


def test_a_connect_through_a_name_that_is_not_local_is_refused() -> None:
    with refused():
        socket.create_connection(("localhost.example.com", 80), timeout=1)


def test_a_refusal_swallowed_by_the_code_under_test_is_still_reported() -> None:
    with suppress(Exception):
        socket.getaddrinfo("example.com", 443)
    assert len(network_guard.disarm()) == 1
    network_guard.arm()


def test_loopback_connections_pass() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        with socket.create_connection(server.getsockname(), timeout=5) as client:
            peer, _ = server.accept()
            peer.close()
            assert client.getpeername() == server.getsockname()


def test_the_ipv6_loopback_passes() -> None:
    if not socket.has_ipv6:
        pytest.skip("this host has no IPv6")
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as server:
        try:
            server.bind(("::1", 0))
        except OSError:
            pytest.skip("this host has no IPv6 loopback")
        server.listen()
        with socket.create_connection(server.getsockname()[:2], timeout=5):
            peer, _ = server.accept()
            peer.close()


@pytest.mark.parametrize("name", ["localhost", "127.0.0.1", "127.0.0.2", "::1", "::ffff:127.0.0.1"])
def test_the_loopback_names_resolve(name: str) -> None:
    assert socket.getaddrinfo(name, 80, flags=socket.AI_NUMERICHOST if name[0] != "l" else 0)


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="this platform has no Unix sockets")
def test_a_unix_socket_passes(tmp_path_factory: pytest.TempPathFactory) -> None:
    path = tmp_path_factory.mktemp("s") / "guard.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        server.listen()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(Path(path)))
            peer, _ = server.accept()
            peer.close()


def test_a_bind_lookup_without_a_host_passes() -> None:
    assert socket.getaddrinfo(None, 0, flags=socket.AI_PASSIVE)


@pytest.mark.network
def test_a_network_test_is_exempt() -> None:
    """Stands for a test that needs a real host: the lookup is numeric, so no packet is sent."""
    assert not network_guard.is_armed()
    assert socket.getaddrinfo(UNROUTABLE, 443, flags=socket.AI_NUMERICHOST)


@pytest.mark.slow
def test_a_slow_test_is_exempt() -> None:
    assert not network_guard.is_armed()
    assert socket.getaddrinfo(UNROUTABLE, 443, flags=socket.AI_NUMERICHOST)


@pytest.mark.parametrize(
    ("host", "local"),
    [
        (None, True),
        ("localhost", True),
        ("LOCALHOST.", True),
        (b"127.0.0.1", True),
        ("::1", True),
        ("::1%lo", True),
        ("::ffff:127.0.0.1", True),
        ("0.0.0.0", False),
        ("", False),
        ("10.0.0.1", False),
        ("::ffff:10.0.0.1", False),
        ("example.com", False),
        (80, False),
    ],
)
def test_which_hosts_are_local(host: object, local: bool) -> None:
    assert network_guard.is_local_host(host) is local
