from email.message import Message

import pytest

from vendors import Answer, annex_vendor, room_vendor


def answer(status: int, retry_after: str | None = None) -> Answer:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return Answer(status, headers, b"")


def test_a_429_waits_as_long_as_it_says():
    assert room_vendor.wait_before_retry(answer(429, retry_after="2")) == 2


@pytest.mark.parametrize(
    "found",
    [
        pytest.param(answer(429), id="a 429 with no Retry-After"),
        pytest.param(
            answer(429, retry_after="soon"), id="a Retry-After that is no number"
        ),
        pytest.param(answer(500), id="a 500"),
        pytest.param(answer(503), id="a 503"),
    ],
)
def test_waits_a_little(found):
    assert room_vendor.wait_before_retry(found) == room_vendor.SHORT_WAIT_S


@pytest.mark.parametrize("status", [200, 400, 403, 404])
def test_asking_the_room_vendor_again_will_not_help(status):
    assert room_vendor.wait_before_retry(answer(status)) is None


def test_busy_waits_as_many_milliseconds_as_it_says():
    busy = {"ok": False, "error": {"code": "BUSY", "retry_after_ms": 1500}}

    assert annex_vendor.wait_before_retry(busy) == 1.5


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"ok": False, "error": {"code": "DAY_CLOSED"}}, id="another code"),
        pytest.param({"ok": True, "result": {"spaces": []}}, id="an answer"),
        pytest.param([], id="no object"),
    ],
)
def test_asking_the_annex_again_will_not_help(body):
    assert annex_vendor.wait_before_retry(body) is None
