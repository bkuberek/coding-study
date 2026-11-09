"""The seam between the API and its vendors: what every vendor looks like."""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from email.message import Message
from http.client import HTTPException
from typing import Protocol
from urllib.error import HTTPError
from urllib.request import urlopen

REQUEST_LIMIT_S = 1.5
"""How long a vendor gets to answer: urllib applies it to each wait on the socket."""


@dataclass(frozen=True)
class Slot:
    room: str
    start: str
    end: str
    vendor: str


class VendorError(Exception):
    """A vendor gave no usable answer."""


class RoomSource(Protocol):
    name: str

    def open_slots(self, day: date) -> list[Slot]:
        """What can be booked on `day`. Raises VendorError without a usable answer."""
        ...


@dataclass(frozen=True)
class Answer:
    status: int
    headers: Message
    body: bytes

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> object:
        try:
            return json.loads(self.body)
        except ValueError as error:
            raise VendorError(f"an answer that is not JSON: {error}") from error


def get(url: str) -> Answer:
    """One request, whatever its status. Raises VendorError when no answer comes."""
    try:
        return _get(url)
    except (OSError, HTTPException) as error:
        raise VendorError(f"no answer from {url}: {error!r}") from error


def _get(url: str) -> Answer:
    try:
        with urlopen(url, timeout=REQUEST_LIMIT_S) as response:
            return Answer(response.status, response.headers, response.read())
    except HTTPError as error:
        with error:
            return Answer(error.code, error.headers, error.read())


def ask_with_retries[T](
    ask: Callable[[], T],
    wait_before_retry: Callable[[T], float | None],
    max_requests: int,
) -> T:
    """Asks until asking again will not help, or `max_requests` are spent.

    `wait_before_retry` reads an answer and gives the seconds to wait before asking
    again, or None when asking again will not help.
    """
    answer = ask()
    for _ in range(max_requests - 1):
        wait = wait_before_retry(answer)
        if wait is None:
            break
        time.sleep(wait)
        answer = ask()
    return answer
