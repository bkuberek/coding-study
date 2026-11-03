"""The steps of the fake language server that the browser tests of code intelligence play
(`tests/fake_language_server.py`): answers that hold for any number of requests, cases that pick
an answer by the request's parameters, and `$uri` and `$dir` standing for the open file."""

import json
import subprocess
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from tests.language_server_scripts import (
    FAKE_LANGUAGE_SERVER,
    ScriptedServer,
    notification,
    request,
)

FILE = "file:///ws/python/practice/two_sum.py"
SORTED = {"kind": "plaintext", "value": "sorted"}


class Client:
    """A page's side of the conversation, over the fake's standard streams."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._process = process

    def send(self, message: dict[str, Any]) -> None:
        body = json.dumps(message).encode()
        assert self._process.stdin is not None
        self._process.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        self._process.stdin.flush()

    def read(self) -> dict[str, Any]:
        assert self._process.stdout is not None
        length = 0
        while line := self._process.stdout.readline().strip():
            name, _, value = line.decode().partition(":")
            if name.lower() == "content-length":
                length = int(value)
        return json.loads(self._process.stdout.read(length))

    def ask(self, request_id: int, method: str, params: object) -> dict[str, Any]:
        self.send(request(request_id, method, params))
        return self.read()

    def open_file(self) -> None:
        document = {"uri": FILE, "languageId": "python", "version": 0, "text": ""}
        self.send(notification("textDocument/didOpen", {"textDocument": document}))


@contextmanager
def playing(tmp_path: Path, *steps: Mapping[str, object]) -> Iterator[Client]:
    script = ScriptedServer(tmp_path / "server.json")
    script.play(*steps)
    process = subprocess.Popen(
        [sys.executable, str(FAKE_LANGUAGE_SERVER), str(script.path), "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    try:
        yield Client(process)
    finally:
        process.kill()
        process.wait()


def hover_at(line: int) -> dict[str, object]:
    return {"textDocument": {"uri": FILE}, "position": {"line": line, "character": 0}}


def test_an_answer_holds_for_every_request_of_its_method(tmp_path: Path):
    with playing(tmp_path, {"answer": {"textDocument/hover": {"contents": SORTED}}}) as client:
        answers = [client.ask(n, "textDocument/hover", hover_at(0)).get("result") for n in (1, 2)]
    assert answers == [{"contents": SORTED}, {"contents": SORTED}]


def test_a_case_answers_by_the_requests_parameters(tmp_path: Path):
    cases = {"cases": [{"when": {"position": {"line": 2}}, "result": "two"}, {"result": "other"}]}
    with playing(tmp_path, {"answer": {"textDocument/hover": cases}}) as client:
        answers = [
            client.ask(n, "textDocument/hover", hover_at(line))["result"]
            for n, line in ((1, 2), (2, 5))
        ]
    assert answers == ["two", "other"]


def test_no_case_that_matches_answers_null(tmp_path: Path):
    cases = {"cases": [{"when": {"position": {"line": 2}}, "result": "two"}]}
    with playing(tmp_path, {"answer": {"textDocument/hover": cases}}) as client:
        answer = client.ask(1, "textDocument/hover", hover_at(7))
    assert answer["result"] is None


def test_a_method_nobody_scripted_is_still_not_found(tmp_path: Path):
    with playing(tmp_path, {"answer": {"textDocument/hover": None}}) as client:
        answer = client.ask(1, "textDocument/definition", hover_at(0))
    assert answer["error"]["code"] == -32601


def test_uri_stands_for_the_file_the_page_opened(tmp_path: Path):
    steps = (
        {"await": "textDocument/didOpen"},
        {"send": {"jsonrpc": "2.0", "method": "x", "params": "$uri"}},
    )
    with playing(tmp_path, *steps) as client:
        client.open_file()
        assert client.read()["params"] == FILE


def test_dir_stands_for_the_folder_of_that_file(tmp_path: Path):
    answer = {"answer": {"textDocument/definition": [{"uri": "$dir/other.py"}]}}
    with playing(tmp_path, {"await": "textDocument/didOpen"}, answer) as client:
        client.open_file()
        result = client.ask(1, "textDocument/definition", hover_at(0))["result"]
    assert result == [{"uri": "file:///ws/python/practice/other.py"}]
