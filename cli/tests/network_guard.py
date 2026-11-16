"""The network guard: an audit hook that keeps the fast tests off the network.

`conftest.py` installs it once per process, because an audit hook cannot be removed, and an
autouse fixture arms it only while a test that is neither `slow` nor `network` runs. Armed, it
refuses `socket.connect` and `socket.getaddrinfo` to anything but a Unix socket, `localhost` or
a loopback address, so nothing in the fast suite can reach a real host, and the fast suite is
what shows that a feature sends nothing with AI off (`docs/specs/ai.md#with-ai-off`).

Every refusal is also recorded, so a test whose code swallows the error still fails at teardown.
"""

import ipaddress
import socket
import sys
from typing import Any

LOCAL_HOSTS = frozenset({"localhost", "localhost.localdomain"})
"""The names that always resolve to the loopback, the one name a test may use instead of an IP."""


class NetworkRefusedError(RuntimeError):
    """A fast test tried to reach a host off the loopback."""


_armed = False
_installed = False
_refusals: list[str] = []


def install() -> None:
    """Add the audit hook to this process, once however often this is called."""
    global _installed
    if not _installed:
        sys.addaudithook(_audit)
        _installed = True


def arm() -> None:
    """Refuse non-local connections from now on, and forget earlier refusals."""
    global _armed
    _refusals.clear()
    _armed = True


def disarm() -> list[str]:
    """Allow every connection again and return what was refused while armed."""
    global _armed
    _armed = False
    refused = list(_refusals)
    _refusals.clear()
    return refused


def is_armed() -> bool:
    return _armed


def is_local_host(host: object) -> bool:
    """Whether `host` is a name or an address on this machine's loopback.

    `None` names no host: `getaddrinfo(None, port)` resolves the loopback or the wildcard for a
    bind, and reaches nothing.
    """
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="replace")
    if not isinstance(host, str):
        return False
    name = host.rstrip(".").lower()
    if name in LOCAL_HOSTS:
        return True
    try:
        address = ipaddress.ip_address(name.partition("%")[0])
    except ValueError:
        return False
    mapped = getattr(address, "ipv4_mapped", None)
    return address.is_loopback or (mapped is not None and mapped.is_loopback)


def _audit(event: str, args: tuple[Any, ...]) -> None:
    if not _armed:
        return
    if event == "socket.connect":
        sock, address = args
        if sock.family == socket.AF_UNIX:
            return
        host = address[0] if isinstance(address, tuple) and address else address
        _check(host, f"socket.connect to {address!r}")
    elif event == "socket.getaddrinfo":
        host = args[0]
        if host is not None:
            _check(host, f"socket.getaddrinfo for {host!r}")


def _check(host: object, what: str) -> None:
    if not is_local_host(host):
        _refuse(what)


def _refuse(what: str) -> None:
    message = (
        f"{what} refused: a fast test may reach only the loopback and Unix sockets; "
        "fix the test to use a fake, or mark it `network` with the reason in its docstring"
    )
    _refusals.append(message)
    raise NetworkRefusedError(message)
