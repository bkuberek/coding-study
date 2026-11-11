"""The broker of a server started ahead of any page (docs/specs/web-ui.md#warm-up): it initializes
the server itself, and the page that takes the server over gets that answer under its own id
instead of initializing it again."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from coding_study.application.code_intelligence import SessionTarget
from coding_study.domain.code_intelligence import BASEDPYRIGHT
from coding_study.entrypoints.web.language_broker import WARM_UP_ID, Delivery, LanguageBroker
from tests.language_server_scripts import answer, notification, request

CAPABILITIES = {"capabilities": {"hoverProvider": True}}
TARGET = SessionTarget(BASEDPYRIGHT, Path("/ws"), "python", Path("/content"))


@pytest.fixture
def broker() -> LanguageBroker:
    return LanguageBroker(TARGET, "9.9.9", 4242)


def from_page(broker: LanguageBroker, message: Any) -> Delivery:
    return asyncio.run(broker.from_page(message))


def from_server(broker: LanguageBroker, message: Any) -> Delivery:
    return broker.from_server(json.dumps(message))


def test_the_broker_initializes_the_server_under_an_id_of_its_own(broker):
    (sent,) = broker.warm_up().to_server

    assert (sent["id"], sent["method"]) == (WARM_UP_ID, "initialize")


def test_its_initialize_is_the_one_a_page_would_get(broker):
    (warm,) = broker.warm_up().to_server
    page = LanguageBroker(TARGET, "9.9.9", 4242)
    (asked,) = from_page(page, request(1, "initialize", {})).to_server

    assert warm["params"] == asked["params"]


def test_the_server_hears_initialized_once_it_answered(broker):
    broker.warm_up()

    delivery = from_server(broker, answer(WARM_UP_ID, CAPABILITIES))

    assert delivery == Delivery(to_server=(notification("initialized", {}),))


def test_a_page_that_takes_the_server_over_gets_its_answer_under_its_own_id(broker):
    broker.warm_up()
    from_server(broker, answer(WARM_UP_ID, CAPABILITIES))

    delivery = from_page(broker, request(7, "initialize", {}))

    assert delivery == Delivery(to_page=(answer(7, CAPABILITIES),))


def test_a_page_that_asks_before_the_server_answered_gets_the_answer_when_it_comes(broker):
    broker.warm_up()
    asked = from_page(broker, request(7, "initialize", {}))

    delivery = from_server(broker, answer(WARM_UP_ID, CAPABILITIES))

    assert (asked, delivery.to_page) == (Delivery(), (answer(7, CAPABILITIES),))


def test_the_pages_initialized_is_not_sent_again(broker):
    broker.warm_up()
    from_server(broker, answer(WARM_UP_ID, CAPABILITIES))
    from_page(broker, request(7, "initialize", {}))

    assert from_page(broker, notification("initialized", {})) == Delivery()


def test_a_second_initialize_of_the_page_is_refused(broker):
    broker.warm_up()
    from_server(broker, answer(WARM_UP_ID, CAPABILITIES))
    from_page(broker, request(7, "initialize", {}))

    (reply,) = from_page(broker, request(8, "initialize", {})).to_page

    assert reply["error"]["message"] == "initialize was already sent"


def test_a_session_the_broker_did_not_warm_sends_its_initialized(broker):
    from_page(broker, request(1, "initialize", {}))

    delivery = from_page(broker, notification("initialized", {}))

    assert delivery.to_server == (notification("initialized", {}),)
