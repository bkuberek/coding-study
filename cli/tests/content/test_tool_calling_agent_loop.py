"""The scripted model of tool-calling-agent-loop-typescript picks each reply by a marker in the
question, and some of its replies quote the starter's system prompt, as a model that obeyed a
planted instruction would. Planted instructions sit in the help center's and the order system's
data as labelled test fixtures. These tests keep the three in step: every question reaches exactly
one scripted conversation, every quoted prompt is the starter's own with its canary, and every
planted instruction says it is a test fixture."""

import json
import re
from collections.abc import Iterator, Mapping
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0292-tool-calling-agent-loop-typescript"
PLANTED_LABEL = "TEST FIXTURE, planted instruction: "
PLANTED_MARK = "planted instruction"
PROMPT_LINE = re.compile(r'^\s+"(?P<line>.+)",$', re.MULTILINE)
CANARY = re.compile(r'export const PROMPT_CANARY = "(?P<canary>[^"]+)";')
FIRST_STEP = [{"role": "system"}, {"role": "user"}]

type Document = Mapping[str, Any]


def mock_config(name: str) -> Document:
    return yaml.safe_load((PROBLEM / "mocks" / f"{name}.yaml").read_text(encoding="utf-8"))


def texts(value: object) -> Iterator[str]:
    """Every string in a value, at any depth, keys left out."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for found in value.values():  # pyright: ignore[reportUnknownVariableType]
            yield from texts(found)  # pyright: ignore[reportUnknownArgumentType]
    elif isinstance(value, list):
        for found in value:  # pyright: ignore[reportUnknownVariableType]
            yield from texts(found)  # pyright: ignore[reportUnknownArgumentType]


def starter_prompt() -> tuple[str, str]:
    """The starter's system prompt, as the app sends it, and its canary."""
    source = (PROBLEM / "starter" / "src" / "prompt.ts").read_text(encoding="utf-8")
    found = CANARY.search(source)
    assert found is not None, "starter/src/prompt.ts declares no PROMPT_CANARY"
    canary = found["canary"]
    lines = [match["line"] for match in PROMPT_LINE.finditer(source)]
    return "\n".join([*lines, f"Canary: {canary}"]), canary


PROMPT, PROMPT_CANARY = starter_prompt()
MODEL_ROUTES: list[Document] = mock_config("model")["routes"]
CASES: list[Document] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))["cases"]


def reply_texts(route: Document) -> list[str]:
    """What a scripted reply says: its answer, or each call's arguments."""
    message = route["response"]["body"]["choices"][0]["message"]
    calls = message.get("tool_calls") or []
    return [message["content"]] if not calls else [call["function"]["arguments"] for call in calls]


def markers() -> set[str]:
    """The text that picks each scripted conversation out of a request's body."""
    return {route["match"]["body_contains"] for route in MODEL_ROUTES if "match" in route}


def answers_a_first_step(route: Document) -> bool:
    """Whether a route can answer a conversation's first request: the system message and the
    question. A route with no messages to match answers every step."""
    messages = route.get("match", {}).get("body", {}).get("messages")
    return messages is None or messages == FIRST_STEP


def scripted_questions() -> list[object]:
    """Each case whose question the model answers, named for its case."""
    return [
        pytest.param(case["request"]["json"]["question"], id=case["id"])
        for case in CASES
        if case["expected"]["status"] == 200
    ]


def planted_texts() -> list[object]:
    """Each text in a tool system's answers that plants an instruction, named for its route."""
    return [
        pytest.param(text, id=f"{system} {route['id']}")
        for system in ("kb", "orders")
        for route in mock_config(system)["routes"]
        for text in texts(route["response"]["body"])
        if PLANTED_MARK in text.lower()
    ]


def leaking_replies() -> list[object]:
    """Each scripted reply that quotes a system prompt, named for its route."""
    return [
        pytest.param(text, id=route["id"])
        for route in MODEL_ROUTES
        for text in reply_texts(route)
        if "Canary:" in text
    ]


@pytest.mark.parametrize("question", scripted_questions())
def test_a_question_holds_exactly_one_conversations_marker(question: str):
    held = [marker for marker in markers() if marker in question]

    assert len(held) == 1, f"{question!r} holds {held}"


@pytest.mark.parametrize("marker", sorted(markers()))
def test_a_marker_starts_its_conversation(marker: str):
    starts = [
        route
        for route in MODEL_ROUTES
        if route.get("match", {}).get("body_contains") == marker and answers_a_first_step(route)
    ]

    assert starts


def test_no_marker_is_in_the_system_prompt():
    assert not [marker for marker in markers() if marker in PROMPT]


def test_the_test_data_plants_instructions():
    assert planted_texts()


@pytest.mark.parametrize("text", planted_texts())
def test_a_planted_instruction_says_it_is_a_test_fixture(text: str):
    assert text.startswith(PLANTED_LABEL)


def test_the_scripted_model_leaks_the_prompt_in_answers_and_in_calls():
    assert len(leaking_replies()) >= 2


@pytest.mark.parametrize("text", leaking_replies())
def test_a_leaking_reply_quotes_the_starters_prompt_with_its_canary(text: str):
    leaked = json.loads(text)["body"] if text.startswith("{") else text

    assert PROMPT in leaked
    assert PROMPT_CANARY in leaked


@pytest.mark.parametrize("system", ["kb", "orders", "helpdesk"])
def test_no_tool_system_holds_the_canary(system: str):
    assert not [text for text in texts(mock_config(system)) if PROMPT_CANARY in text]
