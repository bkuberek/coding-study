"""Seeded inputs for decode-string: an encoding whose decoded length is exactly `n`.

The encoding is built from a decoded-length budget. While budget remains, the builder adds
either a run of 1 to 3 random letters or, with probability 0.5 and below nesting depth 3, a
group `k[...]`. A group usually repeats 1 to 4 times; one group in ten has a count from 10 to
300, so counts with several digits are common. Each group's content gets a budget of at most
8 decoded characters, so groups stay small and their number grows linearly with `n`.

Expanding one innermost group at a time rebuilds the whole string per group, so that brute
force grows with n^2, while the recursive and stack decoders stay linear because the depth is
bounded.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 10**5
MAX_DEPTH = 3
MAX_COUNT = 300
MAX_INNER_BUDGET = 8
GROUP_PROBABILITY = 0.5
LONG_COUNT_PROBABILITY = 0.1


def generate(rng: random.Random, n: int) -> dict:
    encoded, _ = _build(rng, min(max(n, MIN_LENGTH), MAX_LENGTH), 0)
    return {"s": encoded}


def _build(rng: random.Random, budget: int, depth: int) -> tuple[str, int]:
    """An encoding that decodes to exactly `budget` characters, and that length."""
    parts: list[str] = []
    produced = 0
    while produced < budget:
        remaining = budget - produced
        if depth < MAX_DEPTH and remaining >= 2 and rng.random() < GROUP_PROBABILITY:
            if remaining >= 10 and rng.random() < LONG_COUNT_PROBABILITY:
                count = rng.randint(10, min(MAX_COUNT, remaining))
            else:
                count = rng.randint(1, min(4, remaining))
            inner, inner_length = _build(
                rng, rng.randint(1, max(1, min(remaining // count, MAX_INNER_BUDGET))), depth + 1
            )
            parts.append(f"{count}[{inner}]")
            produced += count * inner_length
        else:
            run = min(remaining, rng.randint(1, 3))
            parts.append("".join(rng.choices(string.ascii_lowercase, k=run)))
            produced += run
    return "".join(parts), produced


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert 1 <= len(s) <= MAX_LENGTH, "length out of range"
    lengths = [0]  # decoded length of the text collected at each open level
    counts: list[int] = []
    count = 0
    for character in s:
        if character.isdigit():
            count = count * 10 + int(character)
        elif character == "[":
            assert 1 <= count <= MAX_COUNT, "repeat count out of range"
            counts.append(count)
            lengths.append(0)
            count = 0
        elif character == "]":
            assert counts, "unmatched ]"
            inner = lengths.pop()
            lengths[-1] += inner * counts.pop()
        else:
            assert "a" <= character <= "z", "unexpected character"
            assert count == 0, "digits must be followed by ["
            lengths[-1] += 1
    assert not counts and count == 0, "unclosed group or dangling count"
    assert lengths[0] <= MAX_LENGTH, "decoded string too long"
