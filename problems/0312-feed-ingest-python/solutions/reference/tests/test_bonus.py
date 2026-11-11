import io
import os
from collections.abc import Callable
from email.message import Message
from typing import Any
from urllib.error import HTTPError

import pytest
from bonus import fetch_bonus


@pytest.fixture(autouse=True)
def partner_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(os.environ, "BONUS_URL", "http://partner")


class Answer(io.BytesIO):
    def __enter__(self) -> "Answer":
        return self


def scripted(*steps: object) -> tuple[Callable[..., Any], list[float]]:
    """An opener that plays `steps` in turn, and the pauses taken between attempts."""
    remaining = list(steps)

    def open_url(url: str, timeout: float) -> Answer:
        assert timeout == 1.0
        step = remaining.pop(0)
        if isinstance(step, BaseException):
            raise step
        return Answer(str(step).encode())

    return open_url, []


def failure(code: int, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError("http://partner", code, "failed", headers, None)


def fetch(*steps: object) -> tuple[int | None, list[float]]:
    open_url, _ = scripted(*steps)
    pauses: list[float] = []
    return fetch_bonus("ana", "2027-03", open_url=open_url, sleep=pauses.append), pauses


def test_a_good_answer_is_taken_at_once() -> None:
    assert fetch('{"bonus_points": 25}') == (25, [])


def test_a_failure_is_retried_after_a_backoff_that_doubles() -> None:
    assert fetch(failure(503), TimeoutError(), '{"bonus_points": 7}') == (7, [0.2, 0.4])


def test_three_failures_give_up_with_none() -> None:
    assert fetch(failure(500), failure(500), failure(500)) == (None, [0.2, 0.4])


def test_retry_after_lengthens_the_wait() -> None:
    assert fetch(failure(429, "1"), '{"bonus_points": 1}') == (1, [1.0])


def test_a_refusal_is_not_retried() -> None:
    assert fetch(failure(403)) == (None, [])


def test_no_record_means_no_bonus() -> None:
    assert fetch(failure(404)) == (0, [])


def test_a_body_that_is_not_a_bonus_is_a_failure_to_retry() -> None:
    assert fetch('{"bonus_points": ', '{"points": 1}', '{"bonus_points": -1}') == (None, [0.2, 0.4])
