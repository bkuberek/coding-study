"""A TCP relay: `forward.py <listen port>=<host>:<port> ...`. Standard library only.

A service on an `internal: true` network cannot publish a port, so this small process, joined to
that network and to an ordinary one, carries the app's port and the mock control port to
`127.0.0.1` on your machine. `cstudy` copies this file under `.cs/runs/<run>/` and mounts it
read-only; it holds no user code (docs/specs/service-projects.md#networks).
"""

import asyncio
import signal
import sys
from collections.abc import Awaitable, Callable

_READ_BYTES = 65536

type _Handler = Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Copies until the end of `reader`, then passes the end on, so a client that closes its
    sending side still gets its answer."""
    try:
        while data := await reader.read(_READ_BYTES):
            writer.write(data)
            await writer.drain()
        if writer.can_write_eof():
            writer.write_eof()
    except (ConnectionError, asyncio.CancelledError):
        pass


def _handler(host: str, port: int) -> _Handler:
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            upstream_reader, upstream_writer = await asyncio.open_connection(host, port)
        except OSError:
            writer.close()
            return
        try:
            await asyncio.gather(_pipe(reader, upstream_writer), _pipe(upstream_reader, writer))
        finally:
            upstream_writer.close()
            writer.close()

    return handle


async def _main(specs: list[str]) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for number in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(number, stop.set)
    servers: list[asyncio.Server] = []
    for spec in specs:
        listen, _, target = spec.partition("=")
        host, _, port = target.rpartition(":")
        servers.append(
            await asyncio.start_server(_handler(host, int(port)), "0.0.0.0", int(listen))
        )
    await stop.wait()
    for server in servers:
        server.close()


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1:]))
