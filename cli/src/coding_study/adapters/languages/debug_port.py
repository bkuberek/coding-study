"""The port a debug agent will listen on (docs/specs/runners.md#debug-mode)."""

import socket

from coding_study.domain.debugging import DEBUG_HOST, DebugSession
from coding_study.domain.errors import RunnerStartError


def require_free_port(session: DebugSession) -> None:
    """Raises RunnerStartError when something already listens on the session's port.

    Binds and releases the port; connecting would let an IDE that listens there take the probe
    for its debuggee. A session that connects to the IDE expects its port to be in use.
    """
    if session.connect:
        return
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((DEBUG_HOST, session.port))
        except OSError:
            raise RunnerStartError(
                f"cannot debug {session.language}: port {session.port} on {DEBUG_HOST} is already "
                "in use; stop the other debug session or choose another port with --debug-port"
            ) from None
