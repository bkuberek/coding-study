"""Minimal debugger clients for the `cstudy test --debug` end-to-end tests.

A client does what an IDE does once it attaches: Python speaks the Debug Adapter Protocol to
debugpy, and to Delve as VS Code's Go extension does (`"mode": "remote"`); Node's inspector is
driven by `fixtures/debug/cdp_attach.mjs` (Node has a WebSocket client built in, Python has none);
the JVM only gets the JDWP handshake and a resume; Rust's debug server gets `lldb` in batch mode.
"""

import json
import socket
import struct
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

CDP_CLIENT = Path(__file__).resolve().parent / "fixtures" / "debug" / "cdp_attach.mjs"
CONNECT_TIMEOUT_SECONDS = 30.0
JDWP_HANDSHAKE = b"JDWP-Handshake"
JDWP_HEADER = struct.Struct(">IIBBB")
JDWP_REPLY_FLAG = 0x80
JDWP_VIRTUAL_MACHINE = 1
JDWP_RESUME = 9
HOST = "127.0.0.1"


class DapClient:
    """Attaches to a debug adapter (debugpy by default), stops at a breakpoint, and lets the run
    go on."""

    def __init__(self, port: int, attach: dict[str, Any] | None = None) -> None:
        self._socket = socket.create_connection((HOST, port), timeout=CONNECT_TIMEOUT_SECONDS)
        self._buffer = b""
        self._sequence = 0
        self._thread = 0
        self._attach = attach if attach is not None else {"justMyCode": True}

    def stop_at(self, path: Path, line: int) -> tuple[str, int]:
        """Sets one breakpoint, starts the run and returns the (file, line) it stops at."""
        self._request(
            "initialize", {"clientID": "test", "adapterID": "debugpy", "pathFormat": "path"}
        )
        self._wait(lambda message: message.get("command") == "initialize")
        self._request("attach", self._attach)
        self._wait(lambda message: message.get("event") == "initialized")
        breakpoints = self._request(
            "setBreakpoints", {"source": {"path": str(path)}, "breakpoints": [{"line": line}]}
        )
        self._wait(lambda message: message.get("request_seq") == breakpoints)
        self._request("configurationDone")
        stopped = self._wait(lambda message: message.get("event") == "stopped")
        stack = self._request("stackTrace", {"threadId": stopped["body"]["threadId"], "levels": 1})
        reply = self._wait(lambda message: message.get("request_seq") == stack)
        frame = reply["body"]["stackFrames"][0]
        self._thread = stopped["body"]["threadId"]
        return frame["source"]["path"], frame["line"]

    def finish(self, path: Path) -> None:
        """Removes the breakpoint, resumes the stopped thread and detaches."""
        self._request("setBreakpoints", {"source": {"path": str(path)}, "breakpoints": []})
        self._request("continue", {"threadId": self._thread})
        self._request("disconnect", {"terminateDebuggee": False})
        self._socket.close()

    def run_to_end(self, path: Path) -> None:
        """Removes the breakpoint, resumes, and disconnects once the program ended, as an IDE
        does: Delve ends its debuggee when the client leaves first."""
        self._request("setBreakpoints", {"source": {"path": str(path)}, "breakpoints": []})
        self._request("continue", {"threadId": self._thread})
        self._wait(lambda message: message.get("event") == "terminated")
        self._request("disconnect", {"terminateDebuggee": False})
        self._socket.close()

    def _request(self, command: str, arguments: dict[str, Any] | None = None) -> int:
        self._sequence += 1
        message = {"seq": self._sequence, "type": "request", "command": command}
        message["arguments"] = arguments or {}
        body = json.dumps(message).encode()
        self._socket.sendall(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        return self._sequence

    def _wait(self, wanted: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
        while True:
            message = self._receive()
            if wanted(message):
                return message

    def _receive(self) -> dict[str, Any]:
        while b"\r\n\r\n" not in self._buffer:
            self._buffer += self._read()
        header, rest = self._buffer.split(b"\r\n\r\n", 1)
        length = int(header.split(b":")[1])
        while len(rest) < length:
            rest += self._read()
        self._buffer = rest[length:]
        return json.loads(rest[:length])

    def _read(self) -> bytes:
        chunk = self._socket.recv(65536)
        if not chunk:
            raise ConnectionError("the debug adapter closed the connection")
        return chunk


def run_cdp_client(port: int, path: Path, line: int) -> str:
    """Node's inspector: break at `path:line`, resume, detach; returns what the client printed."""
    completed = subprocess.run(
        ["node", str(CDP_CLIENT), str(port), str(path), str(line)],
        capture_output=True,
        text=True,
        check=True,
        timeout=CONNECT_TIMEOUT_SECONDS * 2,
    )
    return completed.stdout


def run_lldb_client(port: int, path: Path, line: int) -> str:
    """Rust's debug server: connect with `gdb-remote`, break at `path:line`, then run to the end;
    returns what lldb printed."""
    commands = (
        f"gdb-remote {HOST}:{port}",
        f"breakpoint set --file {path} --line {line}",
        "continue",
        "breakpoint delete --force",
        "continue",
    )
    completed = subprocess.run(
        ["lldb", "--batch", *(part for command in commands for part in ("-o", command))],
        capture_output=True,
        text=True,
        check=True,
        timeout=CONNECT_TIMEOUT_SECONDS * 2,
    )
    return completed.stdout


class JdwpClient:
    """The least a JVM started with `suspend=y` needs from a debugger: shake hands and resume."""

    def __init__(self, connection: socket.socket) -> None:
        self._socket = connection

    @classmethod
    def connect(cls, port: int) -> "JdwpClient":
        """Attach to a JVM that listens (`server=y`)."""
        return cls(socket.create_connection((HOST, port), timeout=CONNECT_TIMEOUT_SECONDS))

    @classmethod
    def accept(cls, port: int, timeout_seconds: float = CONNECT_TIMEOUT_SECONDS) -> "JdwpClient":
        """Listen like an IDE's "Remote JVM Debug (listen)" until a JVM (`server=n`) connects."""
        with socket.create_server((HOST, port)) as server:
            server.settimeout(timeout_seconds)
            connection, _ = server.accept()
        connection.settimeout(CONNECT_TIMEOUT_SECONDS)
        return cls(connection)

    def resume(self) -> None:
        self._socket.sendall(JDWP_HANDSHAKE)
        if self._receive(len(JDWP_HANDSHAKE)) != JDWP_HANDSHAKE:
            raise ConnectionError("the JVM did not answer the JDWP handshake")
        size = JDWP_HEADER.size
        self._socket.sendall(JDWP_HEADER.pack(size, 1, 0, JDWP_VIRTUAL_MACHINE, JDWP_RESUME))
        while True:
            length, identifier, flags, error_high, error_low = JDWP_HEADER.unpack(
                self._receive(size)
            )
            self._receive(length - size)
            if flags & JDWP_REPLY_FLAG and identifier == 1:
                if error_high or error_low:
                    raise ConnectionError(f"the JVM refused to resume: {error_high}{error_low}")
                return

    def close(self) -> None:
        self._socket.close()

    def _receive(self, count: int) -> bytes:
        data = b""
        while len(data) < count:
            chunk = self._socket.recv(count - len(data))
            if not chunk:
                raise ConnectionError("the JVM closed the JDWP connection")
            data += chunk
        return data
