"""A client for a running mock server, over real sockets on loopback."""

import http.client
import json
import shutil
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SAMPLE_FOLDER = Path(__file__).parent / "adapters" / "mock_server" / "sample"
SAMPLE_CONFIG = SAMPLE_FOLDER / "mocks.json"
SAMPLE_TOKEN = "sample-token"

GENEROUS_WAIT_S = 30.0
"""The longest any socket, process or poll may take before a test calls it a hang, for a busy
machine. It only ever bounds a wait from above: a test about a delay's lower bound or an ordering
asserts exactly that, however long the machine took."""
POLL_INTERVAL_S = 0.005
HELD_DELAY_MS = int(GENEROUS_WAIT_S * 2 * 1000)
"""A delay no test waits out: a request under it stays in flight for the rest of the test."""


@dataclass(frozen=True)
class Answer:
    status: int
    headers: dict[str, str]
    body: bytes

    def document(self) -> Any:
        return json.loads(self.body)


@dataclass(frozen=True)
class StackClient:
    api_port: int
    control_port: int
    token: str = SAMPLE_TOKEN

    def api(
        self,
        target: str,
        *,
        method: str = "GET",
        host: str = "room-vendor:8080",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Answer:
        return exchange(self.api_port, (method, target), {"Host": host, **(headers or {})}, body)

    def control(
        self,
        target: str,
        *,
        method: str = "GET",
        token: str | None = None,
        body: bytes | None = None,
    ) -> Answer:
        bearer = {"Authorization": f"Bearer {self.token if token is None else token}"}
        return exchange(self.control_port, (method, target), bearer, body)

    def set_scenario(self, mock: str, scenario: str | None) -> None:
        document = json.dumps({"scenario": scenario}).encode()
        answer = self.control(f"/mocks/{mock}/scenario", method="PUT", body=document)
        assert answer.status == 200

    def log(self, mock: str = "room-vendor") -> dict[str, Any]:
        answer = self.control(f"/mocks/{mock}/log")
        assert answer.status == 200
        return answer.document()

    def entries(self, mock: str = "room-vendor") -> list[dict[str, Any]]:
        return self.log(mock)["entries"]

    def hold_a_request(self, target: str, host: str) -> socket.socket:
        """Sends a request and returns its still-open socket, once the mock server has logged it
        as in flight. The caller closes it."""
        mock = host.partition(":")[0]
        before = len(self.entries(mock))
        held = socket.create_connection(("127.0.0.1", self.api_port), timeout=GENEROUS_WAIT_S)
        held.sendall(f"GET {target} HTTP/1.1\r\nHost: {host}\r\n\r\n".encode())
        wait_until(lambda: len(self.entries(mock)) > before)
        return held


def exchange(
    port: int,
    request_line: tuple[str, str],
    headers: dict[str, str],
    body: bytes | None = None,
) -> Answer:
    method, target = request_line
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=GENEROUS_WAIT_S)
    try:
        connection.request(method, target, body=body, headers=headers)
        response = connection.getresponse()
        return Answer(
            response.status,
            {name.lower(): value for name, value in response.getheaders()},
            response.read(),
        )
    finally:
        connection.close()


def send_raw(port: int, request: bytes) -> bytes:
    """What the server answers to exactly these bytes, up to its closing the connection."""
    with socket.create_connection(("127.0.0.1", port), timeout=GENEROUS_WAIT_S) as connection:
        connection.sendall(request)
        received = b""
        while chunk := connection.recv(65536):
            received += chunk
        return received


def wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + GENEROUS_WAIT_S
    while not condition():
        assert time.monotonic() < deadline, f"not within {GENEROUS_WAIT_S} s"
        time.sleep(POLL_INTERVAL_S)


def has_no_answer_yet(held: socket.socket) -> bool:
    held.setblocking(False)
    try:
        held.recv(1)
    except BlockingIOError:
        return True
    return False


def write_config(folder: Path, document: dict[str, Any]) -> Path:
    """A config in `folder`, next to a copy of the sample's body files."""
    shutil.copytree(SAMPLE_FOLDER / "bodies", folder / "bodies")
    path = folder / "mocks.json"
    path.write_text(json.dumps(document))
    return path


def sample_document() -> dict[str, Any]:
    return json.loads(SAMPLE_CONFIG.read_text())


def with_held_scenarios(document: dict[str, Any]) -> dict[str, Any]:
    """Every mock server gains a `held` scenario, whose requests stay in flight."""
    for mock in document["mocks"].values():
        mock["scenarios"]["held"] = {"delay_ms": HELD_DELAY_MS}
    return document
