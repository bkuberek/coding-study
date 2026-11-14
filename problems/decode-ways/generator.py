"""Seeded inputs for decode-ways.

`n` is the length of `s`, clamped to 1..2000. Digits are drawn one at a time, mostly 1 and 2
(which pair with the next digit and make readings ambiguous), with other digits and zeros mixed
in; a zero is placed after a 1 or a 2 so that it can be decoded, except in one input out of
five, which may contain a zero that kills every reading. The generator tracks the number of
readings of the prefix built so far and, whenever the next digit would push it past 2^31 - 1,
appends a digit that does not increase it instead (a 0 after a 1 or 2, else a 9).

From LIVE_FROM digits on (the bench ladder), no input contains a dead zero: a dead zero makes
the top-down search return 0 without ever visiting the suffix after it, so the work would
depend on where the zero falls instead of on n.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 2000
COUNT_LIMIT = 2**31 - 1
DEAD_SHARE = 0.2
ZERO_SHARE = 0.05
AMBIGUOUS_SHARE = 0.6
LIVE_FROM = 100


def _pairs(previous: str, digit: str) -> bool:
    return previous != "" and 10 <= int(previous + digit) <= 26


def _next_count(previous: str, digit: str, two_back: int, one_back: int) -> int:
    count = one_back if digit != "0" else 0
    if _pairs(previous, digit):
        count += two_back
    return count


def _draw(rng: random.Random, previous: str, allow_dead_zero: bool) -> str:
    roll = rng.random()
    if roll < ZERO_SHARE and (allow_dead_zero or previous in ("1", "2")):
        return "0"
    if roll < ZERO_SHARE + AMBIGUOUS_SHARE:
        return rng.choice("12")
    return str(rng.randint(3, 9))


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    allow_dead_zero = rng.random() < DEAD_SHARE and length < LIVE_FROM
    digits: list[str] = []
    previous = ""
    two_back, one_back = 0, 1
    for _ in range(length):
        digit = _draw(rng, previous, allow_dead_zero)
        count = _next_count(previous, digit, two_back, one_back)
        if count > COUNT_LIMIT:
            digit = "0" if previous in ("1", "2") else "9"
            count = _next_count(previous, digit, two_back, one_back)
        digits.append(digit)
        previous = digit
        two_back, one_back = one_back, count
    return {"s": "".join(digits)}


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "length out of range"
    assert all("0" <= digit <= "9" for digit in s), "s must contain digits only"
    previous = ""
    two_back, one_back = 0, 1
    for digit in s:
        two_back, one_back = one_back, _next_count(previous, digit, two_back, one_back)
        previous = digit
        assert one_back <= COUNT_LIMIT, "a prefix has more than 2^31 - 1 readings"
