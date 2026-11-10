"""An LLM gateway stand-in, the real mock server serving the example provider config as two
providers, and the real grader, on loopback with no container: the gateway streams a provider's
events through to its client, falls back to the second provider when a stream breaks, and keeps a
conversation's history, and the cases judge it by what it answered and what it sent."""

import http.client
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from coding_study.adapters.http_grader.clients import open_stack_clients
from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import ListenOn, RunningServers, start_servers
from coding_study.adapters.problem_documents import cases_from_document
from coding_study.application.http_grading import HttpGradingRun, run_http_grading
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.config import Config
from coding_study.domain.judging import Judgement
from coding_study.domain.mock_configs import MockFiles, ScenarioReach, rendered_mock_config
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Problem
from tests.adapters.http_grader.standin_app import AppAnswer, AppRequest, StandInApp, StandInStack
from tests.mock_server_support import (
    LLM_FAKE_KEY,
    LLM_PROVIDER_CONFIG,
    SAMPLE_TOKEN,
)
from tests.project_builders import project_meta

FAST_POLL_S = 0.01
PRIMARY, BACKUP = "primary", "backup"
PROVIDERS = (PRIMARY, BACKUP)
MODEL = "chat-small"
MAX_TOKENS = 256
"""The gateway's budget per request, whatever its client asks for."""
SYSTEM = "You answer questions about desks."
QUESTION = "Which desks are free?"
PROMPT_WORDS = 11
"""The words of the system prompt and the question, their roles included."""
DONE = "[DONE]"
READ_TIMEOUT_S = 1.0
"""How long the gateway waits for a provider's next event before it falls back: a stall."""


def sse(*documents: Any) -> str:
    """Events as the gateway writes them: each document's JSON, and `[DONE]` as it is."""
    return "".join(f"data: {item if item == DONE else json.dumps(item)}\n\n" for item in documents)


def answered_by(provider: str) -> list[Any]:
    usage = {"prompt_tokens": PROMPT_WORDS, "completion_tokens": 3}
    return [
        {"delta": "Oak "},
        {"delta": "is free."},
        {"provider": provider, "model": MODEL, "usage": usage},
        DONE,
    ]


@dataclass
class Gateway:
    """A tiny LLM gateway: it caps `max_tokens`, sends its fake key, streams each event through as
    it comes, and moves to the next provider when a stream ends with no `[DONE]` or stalls."""

    api_port: int
    system_prompt: Callable[[int], str] = lambda _turn: SYSTEM
    """The system prompt for a conversation's turn; a gateway that busts the cache varies it."""
    histories: dict[str, list[dict[str, str]]] = field(
        default_factory=dict[str, list[dict[str, str]]]
    )

    def chat(self, request: AppRequest) -> AppAnswer:
        asked = json.loads(request.body)
        history = self.histories.setdefault(asked["conversation"], [])
        history.append({"role": "user", "content": asked["message"]})
        system = {"role": "system", "content": self.system_prompt(len(history))}
        body = {
            "model": MODEL,
            "messages": [system, *history],
            "max_tokens": min(asked["max_tokens"], MAX_TOKENS),
            "stream": True,
        }
        return AppAnswer(200, stream=self._relayed(body, history))

    def _relayed(self, body: dict[str, Any], history: list[dict[str, str]]) -> Iterator[bytes]:
        for provider in PROVIDERS:
            texts: list[str] = []
            first: dict[str, Any] = {}
            for data in self._events(provider, body):
                if data == DONE:
                    history.append({"role": "assistant", "content": "".join(texts)})
                    ending = {
                        "provider": provider,
                        "model": first["model"],
                        "usage": first["usage"],
                    }
                    yield sse(ending, DONE).encode()
                    return
                chunk = json.loads(data)
                first.setdefault("model", chunk.get("model"))
                if "usage" in chunk:
                    first["usage"] = chunk["usage"]
                for choice in chunk["choices"]:
                    text = choice["delta"].get("content")
                    if text:
                        texts.append(text)
                        yield sse({"delta": text}).encode()
            yield sse({"retry": provider}).encode()
        yield sse({"error": "every provider failed"}).encode()

    def _events(self, provider: str, body: dict[str, Any]) -> Iterator[str]:
        connection = http.client.HTTPConnection("127.0.0.1", self.api_port, timeout=READ_TIMEOUT_S)
        headers = {
            "Host": f"{provider}:8080",
            "Authorization": f"Bearer {LLM_FAKE_KEY}",
            "Content-Type": "application/json",
        }
        try:
            connection.request("POST", "/v1/chat/completions", json.dumps(body), headers)
            response = connection.getresponse()
            while line := response.readline():
                text = line.decode().rstrip("\n")
                if text.startswith("data: "):
                    yield text.removeprefix("data: ")
        except TimeoutError:
            return
        finally:
            connection.close()


@pytest.fixture
def providers(tmp_path: Path) -> Iterator[RunningServers]:
    """The example config served twice, as two providers on one API port."""
    files = MockFiles(yaml.safe_load(LLM_PROVIDER_CONFIG.read_text()))
    rendered = rendered_mock_config(
        dict.fromkeys(PROVIDERS, files), SAMPLE_TOKEN, ScenarioReach.EVERY
    )
    path = tmp_path / "mocks.json"
    path.write_text(rendered)
    servers = start_servers(load_stack_config(path), ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    yield servers
    servers.close()


@dataclass
class Graded:
    judgement: Judgement

    def statuses(self) -> list[CaseStatus]:
        return [verdict.status for verdict in self.judgement.verdicts]

    def reasons(self) -> list[str | None]:
        verdicts = self.judgement.verdicts
        return [verdict.mismatch.detail if verdict.mismatch else None for verdict in verdicts]


type Grade = Callable[..., Graded]


@pytest.fixture
def grade(providers: RunningServers) -> Iterator[Grade]:
    apps: list[StandInApp] = []

    def run(*documents: dict[str, Any]) -> Graded:
        steady = Gateway(providers.api_port)
        busting = Gateway(providers.api_port, lambda turn: f"{SYSTEM} Turn {turn}.")
        routes = {("POST", "/chat"): steady.chat, ("POST", "/chat-busting"): busting.chat}
        app = StandInApp(routes)
        apps.append(app)
        stack = StandInStack(app, providers.control_port, mocks=PROVIDERS)
        comparator = ComparatorSpec(ComparatorType.EXACT)
        cases = cases_from_document(
            {"version": 1, "cases": list(documents)}, comparator, "tests.json"
        )
        problem = Problem(project_meta(comparator=comparator), cases)
        run = HttpGradingRun(problem, 1, Config())
        return Graded(run_http_grading(run, stack, open_stack_clients))

    yield run
    for app in apps:
        app.close()


def asking(conversation: str, path: str = "/chat") -> dict[str, Any]:
    question = {"conversation": conversation, "message": QUESTION, "max_tokens": 4096}
    return {"method": "POST", "path": path, "json": question}


def streamed_case(**fields: Any) -> dict[str, Any]:
    return {
        "id": "h1",
        "level": 1,
        "request": asking("c-stream"),
        "expected": {"status": 200, "body": sse(*answered_by(PRIMARY))},
        **fields,
    }


def test_a_stream_through_the_gateway_passes(grade: Grade):
    assert grade(streamed_case()).statuses() == [CaseStatus.PASS]


def test_the_gateway_streams_with_its_fake_key_and_a_capped_budget(grade: Grade):
    log = [
        {
            "mock": PRIMARY,
            "route": "chat-stream",
            "count": 1,
            "headers": {"Authorization": f"Bearer {LLM_FAKE_KEY}"},
            "body": {"model": MODEL, "stream": True},
            "body_max": {"max_tokens": MAX_TOKENS},
        },
        {"mock": BACKUP, "count": 0},
    ]
    assert grade(streamed_case(log=log)).statuses() == [CaseStatus.PASS]


def test_a_budget_the_gateway_did_not_keep_fails_on_the_log(grade: Grade):
    log = [{"mock": PRIMARY, "route": "chat-stream", "count": 1, "body_max": {"max_tokens": 64}}]
    assert grade(streamed_case(log=log)).reasons() == [
        "primary chat-stream with body max_tokens at most 64: expected 1 request, saw 0"
    ]


def test_a_dropped_stream_falls_back_to_the_second_provider_with_the_same_messages(grade: Grade):
    events = [{"delta": "Oak "}, {"retry": PRIMARY}, *answered_by(BACKUP)]
    same = {"mock": PRIMARY, "route": "chat-stream", "fields": ["messages"]}
    case = streamed_case(
        request=asking("c-drop"),
        mocks={PRIMARY: "dropped_mid_stream"},
        expected={"status": 200, "body": sse(*events)},
        log=[{"mock": BACKUP, "route": "chat-stream", "count": 1, "body_same_as": same}],
    )
    assert grade(case).statuses() == [CaseStatus.PASS]


def test_a_stalled_stream_falls_back_once_the_gateway_gives_up(grade: Grade):
    events = [{"delta": "Oak "}, {"retry": PRIMARY}, *answered_by(BACKUP)]
    case = streamed_case(
        request=asking("c-stall"),
        mocks={PRIMARY: "stalled_stream"},
        expected={"status": 200, "body": sse(*events)},
    )
    assert grade(case).statuses() == [CaseStatus.PASS]


def conversation_case(path: str) -> dict[str, Any]:
    turn = {"request": asking(f"c-cache{path}", path), "expected": {"status": 200}}
    prefix = {"mock": PRIMARY, "route": "chat-stream", "count": 2, "body_prefix_stable": "messages"}
    return {"id": "h2", "level": 1, "steps": [turn, turn], "log": [prefix]}


def test_a_history_that_only_grows_keeps_the_prefix_stable(grade: Grade):
    assert grade(conversation_case("/chat")).statuses() == [CaseStatus.PASS]


def test_a_system_prompt_that_changes_each_turn_breaks_the_prefix(grade: Grade):
    assert grade(conversation_case("/chat-busting")).reasons() == [
        "primary chat-stream: body messages of request 2 does not start with request 1's: "
        "element 0 differs"
    ]
