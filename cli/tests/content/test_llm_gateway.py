"""The cases of llm-gateway-typescript carry numbers worked out when they were written: each
answer's token usage, which the mock providers count as the words of the messages, its text, each
team's cost from the statement's price table, and the `max_tokens` a budget leaves. These tests
work them out again from the mock configs and the statement, so a case expects only what the
providers and the rules give."""

import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0290-llm-gateway-typescript"
PRIMARY, SECONDARY = "primary", "secondary"
DEFAULT_MAX_TOKENS = 256
DONE = "[DONE]"
FIRST_GRADED_LEVEL_WITH_BUDGETS = 4

type Document = Mapping[str, Any]


def mock_routes(name: str) -> dict[str, Document]:
    config = yaml.safe_load((PROBLEM / "mocks" / f"{name}.yaml").read_text(encoding="utf-8"))
    return {route["id"]: route["response"] for route in config["routes"]}


PRIMARY_WHOLE = mock_routes(PRIMARY)["chat"]["body"]
SECONDARY_WHOLE = mock_routes(SECONDARY)["messages"]["body"]
TEXT = {
    PRIMARY: PRIMARY_WHOLE["choices"][0]["message"]["content"],
    SECONDARY: SECONDARY_WHOLE["output"]["text"],
}
COMPLETION_TOKENS = {
    PRIMARY: PRIMARY_WHOLE["usage"]["completion_tokens"],
    SECONDARY: SECONDARY_WHOLE["usage"]["output_tokens"],
}
LIMIT_FIELD = {PRIMARY: "max_tokens", SECONDARY: "max_output_tokens"}
PRICE_ROW = re.compile(r"^\| (primary|secondary) \| `[^`]+` \| (\d+) \| (\d+) \|$", re.MULTILINE)
PRICES = {
    provider: (int(prompt), int(completion))
    for provider, prompt, completion in PRICE_ROW.findall(
        (PROBLEM / "problem.md").read_text(encoding="utf-8")
    )
}
CASES: list[Document] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))["cases"]


def words(value: object) -> int:
    """What the mock server's `words(...)` counts: the words of every text, at any depth."""
    if isinstance(value, str):
        return len(value.split())
    if isinstance(value, list):
        return sum(words(item) for item in value)
    if isinstance(value, dict):
        return sum(words(item) for item in value.values())
    return 0


@dataclass(frozen=True)
class Exchange:
    """One request of a case and the answer it expects; a `before` request expects a 2xx."""

    request: Document
    expected: Document


def exchanges(case: Document) -> list[Exchange]:
    before = [Exchange(request, {"status": 200}) for request in case.get("before", [])]
    if "steps" in case:
        return before + [Exchange(step["request"], step["expected"]) for step in case["steps"]]
    return [*before, Exchange(case["request"], case["expected"])]


def is_chat(request: Document) -> bool:
    return request["method"] == "POST" and request["path"] == "/v1/chat"


def events(stream: str) -> list[tuple[str, str]]:
    """Each event of an expected stream: its name, `message` when it has none, and its data."""
    found: list[tuple[str, str]] = []
    for block in stream.split("\n\n")[:-1]:
        name, data = "message", ""
        for line in block.split("\n"):
            label, _, value = line.partition(": ")
            if label == "event":
                name = value
            elif label == "data":
                data = value
        found.append((name, data))
    return found


def answered_chats() -> Iterator[tuple[str, Document, Document]]:
    """Each chat request that expects a 200 with a body, with its case's id."""
    for case in CASES:
        for exchange in exchanges(case):
            expected = exchange.expected
            if is_chat(exchange.request) and expected["status"] == 200 and "body" in expected:
                yield case["id"], exchange.request, expected["body"]


def usages(body: object) -> list[Document]:
    """The usage a whole answer or a stream's usage event carries, with its provider."""
    if isinstance(body, dict):
        return [body]
    return [json.loads(data) for _name, data in events(str(body)) if '"usage"' in data]


ANSWERS = list(answered_chats())
ANSWER_PARAMS = [pytest.param(request, body, id=case_id) for case_id, request, body in ANSWERS]
STREAMS = [(case_id, body) for case_id, _request, body in ANSWERS if isinstance(body, str)]


@pytest.mark.parametrize(("request_", "body"), ANSWER_PARAMS)
def test_prompt_tokens_are_the_words_of_the_messages(request_: Document, body: Any):
    for usage in usages(body):
        assert usage["usage"]["prompt_tokens"] == words(request_["json"]["messages"])


@pytest.mark.parametrize(("request_", "body"), ANSWER_PARAMS)
def test_completion_tokens_are_the_answering_provider_s(request_: Document, body: Any):
    for usage in usages(body):
        assert usage["usage"]["completion_tokens"] == COMPLETION_TOKENS[usage["provider"]]


@pytest.mark.parametrize(("case_id", "body"), STREAMS, ids=[s[0] for s in STREAMS])
def test_a_stream_ends_in_done_or_in_one_error_event_never_both(case_id: str, body: str):
    endings = [(name, data) for name, data in events(body) if name == "error" or data == DONE]

    assert endings == [events(body)[-1]]


def streamed_text(body: str) -> str:
    return "".join(json.loads(data)["delta"] for _name, data in events(body) if '"delta"' in data)


FINISHED = [(case_id, body) for case_id, body in STREAMS if body.endswith(f"data: {DONE}\n\n")]
BROKEN = [(case_id, body) for case_id, body in STREAMS if (case_id, body) not in FINISHED]


@pytest.mark.parametrize(("case_id", "body"), FINISHED, ids=[s[0] for s in FINISHED])
def test_a_finished_stream_s_text_is_its_provider_s_answer(case_id: str, body: str):
    assert streamed_text(body) == TEXT[usages(body)[0]["provider"]]


@pytest.mark.parametrize(("case_id", "body"), BROKEN, ids=[s[0] for s in BROKEN])
def test_a_broken_stream_s_text_is_the_start_of_its_provider_s_answer(case_id: str, body: str):
    provider = answering_provider(case_of(case_id))

    assert TEXT[provider].startswith(streamed_text(body))


def case_of(case_id: str) -> Document:
    return next(case for case in CASES if case["id"] == case_id)


def answering_provider(case: Document) -> str:
    """The secondary when a case takes the primary down, which every budget case does with
    `outage` alone; the primary otherwise."""
    return SECONDARY if case.get("mocks", {}).get(PRIMARY) == "outage" else PRIMARY


@dataclass
class Account:
    budget: int | None = None
    prompt: int = 0
    completion: int = 0
    cost: int = 0

    def remaining(self) -> int | None:
        return None if self.budget is None else max(0, self.budget - self.prompt - self.completion)


@dataclass
class Ledger:
    """The statement's rules for budgets and cost, over one case's requests in order."""

    provider: str
    accounts: dict[str, Account] = field(default_factory=dict[str, Account])
    limits_sent: list[int] = field(default_factory=list[int])

    def account(self, team: str) -> Account:
        return self.accounts.setdefault(team, Account())

    def chat(self, team: str, request: Document, status: int) -> None:
        account = self.account(team)
        remaining = account.remaining()
        if status == 429:
            assert remaining == 0
            return
        if status != 200:
            return
        asked = request["json"].get("max_tokens", DEFAULT_MAX_TOKENS)
        self.limits_sent.append(asked if remaining is None else min(asked, remaining))
        prompt, completion = words(request["json"]["messages"]), COMPLETION_TOKENS[self.provider]
        prompt_price, completion_price = PRICES[self.provider]
        account.prompt += prompt
        account.completion += completion
        account.cost += prompt * prompt_price + completion * completion_price

    def usage(self, team: str) -> dict[str, object]:
        account = self.account(team)
        return {
            "team": team,
            "prompt_tokens": account.prompt,
            "completion_tokens": account.completion,
            "cost_micros": account.cost,
            "remaining_tokens": account.remaining(),
        }


def team_of(request: Document) -> str:
    """The `X-Team` of a chat, which a refused one may lack, or the team a team route names."""
    if is_chat(request):
        return request.get("headers", {}).get("X-Team", "")
    return request["path"].split("/")[3]


def replayed(case: Document) -> Ledger:
    """A case's requests through the ledger, checking each usage it expects on the way."""
    ledger = Ledger(answering_provider(case))
    for exchange in exchanges(case):
        request, status = exchange.request, exchange.expected["status"]
        team = team_of(request)
        if is_chat(request):
            ledger.chat(team, request, status)
        elif request["method"] == "PUT" and status == 200:
            ledger.account(team).budget = request["json"]["tokens"]
        elif request["method"] == "GET":
            assert exchange.expected["body"] == ledger.usage(team), case["id"]
    return ledger


BUDGET_CASES = [case for case in CASES if case["level"] >= FIRST_GRADED_LEVEL_WITH_BUDGETS]


@pytest.mark.parametrize("case", BUDGET_CASES, ids=[case["id"] for case in BUDGET_CASES])
def test_each_usage_answer_follows_from_the_answers_and_the_price_table(case: Document):
    replayed(case)


@pytest.mark.parametrize("case", BUDGET_CASES, ids=[case["id"] for case in BUDGET_CASES])
def test_each_limit_a_case_expects_a_provider_to_be_sent_is_what_the_budget_leaves(case: Document):
    ledger = replayed(case)
    limit = LIMIT_FIELD[ledger.provider]
    for entry in case.get("log", []):
        if limit in entry.get("body", {}):
            assert ledger.limits_sent.count(entry["body"][limit]) == entry["count"], case["id"]


def test_each_budget_case_has_teams_no_other_case_touches():
    """An app keeps its teams for a whole graded run, so a budget case that shared a team with
    another case would start from that case's usage."""
    teams_by_case = {case["id"]: {team_of(e.request) for e in exchanges(case)} for case in CASES}
    for case in BUDGET_CASES:
        others = set[str]().union(
            *(teams for case_id, teams in teams_by_case.items() if case_id != case["id"])
        )
        assert not teams_by_case[case["id"]] & others, case["id"]


def test_the_price_table_names_both_providers():
    assert set(PRICES) == {PRIMARY, SECONDARY}


SLOW_STREAM = "slow_stream"
TIMING_MARGIN_MS = 500
"""What a busy machine may add to a stream's first byte, or take from a held-back one's lead."""


def slow_stream_events() -> list[Document]:
    config = yaml.safe_load((PROBLEM / "mocks" / f"{PRIMARY}.yaml").read_text(encoding="utf-8"))
    return config["scenarios"][SLOW_STREAM]["stream"]


def test_the_slow_stream_s_first_byte_limit_lies_well_between_its_first_event_and_its_end():
    """A gateway that streams sends its first byte soon after the first event, and one that holds
    the stream back sends it after the last, so the limit tells them apart on a busy machine."""
    events = slow_stream_events()
    first_event_ms = events[0].get("after_ms", 0)
    end_ms = sum(event.get("after_ms", 0) for event in events)
    (case,) = [case for case in CASES if case.get("mocks", {}).get(PRIMARY) == SLOW_STREAM]
    limit_ms = case["expected"]["first_byte_ms_max"]
    assert first_event_ms + TIMING_MARGIN_MS <= limit_ms <= end_ms - TIMING_MARGIN_MS
