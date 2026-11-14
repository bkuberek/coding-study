"""The bonus partner's client: bounded retries with backoff, and a timeout on every attempt.

A lookup either answers with a bonus or gives up and answers None. It never raises for what the
partner does, so one bad member cannot fail a whole reconciliation.
"""

import json
import os
import time
from collections.abc import Callable
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

MAX_ATTEMPTS = 3
TIMEOUT_S = 1.0
FIRST_BACKOFF_S = 0.2
NO_RECORD = 404
TOO_MANY_REQUESTS = 429


def read_bonus(body: bytes) -> int | None:
    """The bonus in an answer's body, or None when the body is not what the partner promises."""
    try:
        value = json.loads(body)["bonus_points"]
    except (ValueError, KeyError, TypeError):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def retry_after_s(error: HTTPError) -> float:
    header = error.headers.get("Retry-After", "")
    return float(header) if header.isascii() and header.isdigit() else 0.0


def fetch_bonus(
    member: str,
    month: str,
    *,
    open_url: Callable[..., Any] = urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> int | None:
    """The bonus the partner grants `member` for `month`, or None when it could not be learned."""
    url = f"{os.environ['BONUS_URL']}/v1/bonus?{urlencode({'member': member, 'month': month})}"
    backoff = FIRST_BACKOFF_S
    for attempt in range(MAX_ATTEMPTS):
        wait = backoff
        try:
            with open_url(url, timeout=TIMEOUT_S) as answer:
                bonus = read_bonus(answer.read())
            if bonus is not None:
                return bonus
        except HTTPError as error:
            if error.code == NO_RECORD:
                return 0
            if error.code != TOO_MANY_REQUESTS and error.code < 500:
                return None
            wait = max(wait, retry_after_s(error))
        except (OSError, HTTPException):
            pass
        if attempt < MAX_ATTEMPTS - 1:
            sleep(wait)
            backoff *= 2
    return None
