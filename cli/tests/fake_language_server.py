"""A stand-in for a language server (docs/specs/web-ui.md#testing): it speaks LSP over its standard
streams and plays a script, as `tests/scripted_child.py` plays one for a child `cstudy`.

    python fake_language_server.py <script.json> [<server script>] [--stdio | --version]

It appends its pid, arguments, current directory and the two environment variables that hide
directories from a Node server (`NODE_OPTIONS`, `CSTUDY_HIDDEN_DIRECTORIES`) as one JSON line to
`<script>.calls` and every message it reads as one JSON line to `<script>.received`, then plays the
script's steps in order, each an object with one key:

    {"send": <message>}                      writes a message to standard output
    {"answer": {"<method>": <result>, …}}    from now on answers every request of each method
                                             with its result, however often and whenever it
                                             comes; a value {"cases": [{"when": <subset of the
                                             request's params>, "result": …}, …]} answers with
                                             the first case whose `when` the params contain (a
                                             case without `when` always matches), else null
    {"reply": "<method>", "result": <value>} waits for a request of that method and answers it;
                                             with "error": <object> in place of "result", an error
    {"await": "<method>"}                    waits for a message of that method
    {"await_response": <id>}                 waits for the answer to the request with that id
    {"err": "<line>"}                        writes a line to standard error
    {"raw": "<text>"}                        writes the text to standard output as it is
    {"wait_for": "<path>"}                   waits until the file exists
    {"exit": <code>}                         exits
    {"ignore": ["shutdown", "exit", "eof", "SIGTERM"]}   stops honouring what it names
    {"deaf": true}                           stops reading its standard input after the message
                                             it is reading, so the pipe fills and nothing it
                                             was sent is answered, `shutdown` and `exit` included
    {"spawn_sleeper": "<path>"}              starts a process that ignores SIGINT and SIGTERM in
                                             this one's process group, and writes its pid

In what it sends and answers, and in the `when` of a case, the text `$uri` stands for the URI
of the file of the last `textDocument/didOpen` it read, and `$dir` for the folder that file is
in, so a script can point at the tab's file before the test knows where the workspace is.

After the last step it creates `<script>.ready`, answers `shutdown` with null, exits on `exit`
and at the end of its standard input, answers any other request with -32601 and ignores
notifications, unless it was told to ignore one of them. `--version` prints what the pinned
server's version command prints and exits. It imports the standard library only, so it starts
fast.
"""

import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, NoReturn

SLEEPER = (
    "import signal, time; signal.signal(signal.SIGINT, signal.SIG_IGN); "
    "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(120)"
)
VERSIONS = {"basedpyright": "basedpyright 1.40.2", "typescript-language-server": "6.0.3"}
POLL_S = 0.01
METHOD_NOT_FOUND = -32601

type Message = dict[str, Any]


class Inbox:
    """The messages from standard input, read by a thread of their own, so a step that waits for
    one never blocks the exit on end of file."""

    def __init__(self, log: Path) -> None:
        self._log = log
        self._messages: queue.Queue[Message | None] = queue.Queue()
        self._deaf = threading.Event()
        threading.Thread(target=self._read, daemon=True).start()

    def get(self) -> Message | None:
        return self._messages.get()

    def go_deaf(self) -> None:
        self._deaf.set()

    def _read(self) -> None:
        stream = sys.stdin.buffer
        while not self._deaf.is_set():
            length = _content_length(stream)
            if length is None:
                self._messages.put(None)
                return
            body = stream.read(length)
            with self._log.open("a", encoding="utf-8") as log:
                log.write(body.decode() + "\n")
            self._messages.put(_parsed(body))


def _parsed(body: bytes) -> Message:
    try:
        return json.loads(body)
    except ValueError:
        return {"unparsed": body.decode()}


def _content_length(stream: Any) -> int | None:
    length = None
    while line := stream.readline():
        header = line.decode().strip()
        if not header:
            return length
        name, _, value = header.partition(":")
        if name.lower() == "content-length":
            length = int(value)
    return None


class Server:
    def __init__(self, script: Path) -> None:
        self.ready = script.with_suffix(".ready")
        self.ignored: set[str] = set()
        self.inbox = Inbox(script.with_suffix(".received"))
        self.answers: dict[str, Any] = {}
        self.opened = ""
        """The URI of the file of the last `didOpen`."""

    def next(self) -> Message | None:
        message = self.inbox.get()
        if message is not None and message.get("method") == "textDocument/didOpen":
            document = (message.get("params") or {}).get("textDocument") or {}
            self.opened = document.get("uri", self.opened)
        return message

    def filled(self, value: Any) -> Any:
        """`value` with `$uri` and `$dir` replaced in every string."""
        if isinstance(value, str):
            folder = self.opened.rsplit("/", 1)[0]
            return value.replace("$uri", self.opened).replace("$dir", folder)
        if isinstance(value, list):
            return [self.filled(item) for item in value]
        if isinstance(value, dict):
            return {key: self.filled(item) for key, item in value.items()}
        return value

    def play(self, steps: list[dict[str, Any]]) -> None:
        for step in steps:
            [(name, value)] = [item for item in step.items() if item[0] in STEPS]
            STEPS[name](self, value, step)

    def run(self) -> None:
        self.ready.touch()
        while True:
            self.handle(self.next())

    def wait_for_message(self, matches: Any) -> Message:
        while True:
            message = self.next()
            if message is not None and matches(message):
                return message
            self.handle(message)

    def handle(self, message: Message | None) -> None:
        """What a server does with a message nobody scripted."""
        if message is None:
            while "eof" in self.ignored:
                signal.pause()
            exit_with(0)
        method = message.get("method")
        if method == "exit":
            if "exit" not in self.ignored:
                exit_with(0)
        elif method == "shutdown":
            if "shutdown" not in self.ignored:
                send({"jsonrpc": "2.0", "id": message["id"], "result": None})
        elif "id" in message and method in self.answers:
            result = self.filled(self.result_for(self.answers[method], message.get("params")))
            send({"jsonrpc": "2.0", "id": message["id"], "result": result})
        elif "id" in message and method is not None:
            error = {"code": METHOD_NOT_FOUND, "message": f"no {method}"}
            send({"jsonrpc": "2.0", "id": message["id"], "error": error})

    def result_for(self, answer: Any, params: Any) -> Any:
        if not (isinstance(answer, dict) and "cases" in answer):
            return answer
        for case in answer["cases"]:
            if "when" not in case or contains(params, self.filled(case["when"])):
                return case["result"]
        return None


def contains(actual: Any, expected: Any) -> bool:
    """Whether `actual` holds everything `expected` names: the same value, or for an object the
    same values at its keys, whatever else it has."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(
            key in actual and contains(actual[key], value) for key, value in expected.items()
        )
    return bool(actual == expected)


def send(message: Message) -> None:
    body = json.dumps(message).encode()
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    sys.stdout.buffer.flush()


def exit_with(code: int) -> NoReturn:
    sys.stdout.flush()
    os._exit(code)


def step_send(server: Server, message: Any, _step: dict[str, Any]) -> None:
    send(server.filled(message))


def step_answer(server: Server, answers: Any, _step: dict[str, Any]) -> None:
    server.answers.update(answers)


def step_reply(server: Server, method: Any, step: dict[str, Any]) -> None:
    request = server.wait_for_message(lambda m: m.get("method") == method and "id" in m)
    answer = {"error": step["error"]} if "error" in step else {"result": step.get("result")}
    send({"jsonrpc": "2.0", "id": request["id"], **server.filled(answer)})


def step_await(server: Server, method: Any, _step: dict[str, Any]) -> None:
    server.wait_for_message(lambda m: m.get("method") == method)


def step_await_response(server: Server, request_id: Any, _step: dict[str, Any]) -> None:
    server.wait_for_message(lambda m: m.get("id") == request_id and "method" not in m)


def step_err(_server: Server, line: Any, _step: dict[str, Any]) -> None:
    print(line, file=sys.stderr, flush=True)


def step_raw(_server: Server, text: Any, _step: dict[str, Any]) -> None:
    sys.stdout.buffer.write(str(text).encode())
    sys.stdout.buffer.flush()


def step_wait_for(_server: Server, path: Any, _step: dict[str, Any]) -> None:
    while not Path(str(path)).exists():
        time.sleep(POLL_S)


def step_exit(_server: Server, code: Any, _step: dict[str, Any]) -> None:
    exit_with(int(code))


def step_ignore(server: Server, names: Any, _step: dict[str, Any]) -> None:
    server.ignored.update(names)
    if "SIGTERM" in names:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)


def step_deaf(server: Server, _value: Any, _step: dict[str, Any]) -> None:
    server.inbox.go_deaf()


def step_spawn_sleeper(_server: Server, pid_path: Any, _step: dict[str, Any]) -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", SLEEPER], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    Path(str(pid_path)).write_text(str(process.pid))


STEPS = {
    "send": step_send,
    "answer": step_answer,
    "reply": step_reply,
    "await": step_await,
    "await_response": step_await_response,
    "err": step_err,
    "raw": step_raw,
    "wait_for": step_wait_for,
    "exit": step_exit,
    "ignore": step_ignore,
    "deaf": step_deaf,
    "spawn_sleeper": step_spawn_sleeper,
}


def main(script_path: str, arguments: list[str]) -> None:
    script = Path(script_path)
    pinned = next((name for name in VERSIONS if name in " ".join(arguments)), None)
    if "--version" in arguments and pinned is not None:
        print(VERSIONS[pinned])
        return
    with script.with_suffix(".calls").open("a", encoding="utf-8") as calls:
        record = {
            "pid": os.getpid(),
            "arguments": arguments,
            "cwd": str(Path.cwd()),
            "node_options": os.environ.get("NODE_OPTIONS"),
            "hidden": os.environ.get("CSTUDY_HIDDEN_DIRECTORIES"),
        }
        calls.write(json.dumps(record) + "\n")
    server = Server(script)
    server.play(json.loads(script.read_text(encoding="utf-8")))
    server.run()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
