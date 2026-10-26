"""Seeded inputs for almost-palindrome: palindromes with one or two inserted characters.

Every input starts as a random palindrome and gets one or two extra characters:

- one extra character somewhere in the middle half of the string, so deleting it restores
  the palindrome (the answer is true but needs a deletion);
- two extra characters, one in each half at positions that do not mirror each other, so the
  answer is almost always false.

Inputs shorter than 100 characters, which include the oracle's, take either shape with equal
chance, so both answers are common. Longer inputs, the ones the ladder times, always take the
second shape: a solution that tries every deletion then tries all n of them at every seed,
instead of stopping at an insertion whose position changes from seed to seed.

No input is a palindrome as generated. Some inputs use a three-letter alphabet, where the two
candidate deletions at the first mismatch often both look plausible for a while.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 10**5
ALPHABETS = (string.ascii_lowercase, "abc")
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    alphabet = rng.choice(ALPHABETS)
    insertions = _insertions(rng, length)
    letters = _palindrome(rng, alphabet, length - insertions)
    if insertions == 1:
        letters.insert(rng.randint(length // 4, (3 * length) // 4), rng.choice(alphabet))
    else:
        right = rng.randint(length // 2 + 1, (3 * length) // 4)
        letters.insert(right - 1, rng.choice(alphabet))
        left = rng.randint(length // 4, length // 2 - 1)
        if left == length - 1 - right:
            left -= 1
        letters.insert(left, rng.choice(alphabet))
    return {"s": "".join(letters)}


def validate(case_input: dict) -> None:
    text = case_input["s"]
    assert MIN_LENGTH <= len(text) <= MAX_LENGTH, "length out of range"
    assert all("a" <= ch <= "z" for ch in text), "only lowercase letters are allowed"


def _insertions(rng: random.Random, length: int) -> int:
    if length < 4:
        return 1
    if length >= UNIFORM_FROM:
        return 2
    return 2 if rng.random() < 0.5 else 1


def _palindrome(rng: random.Random, alphabet: str, count: int) -> list[str]:
    half = [rng.choice(alphabet) for _ in range(count // 2)]
    middle = [rng.choice(alphabet)] if count % 2 else []
    return half + middle + half[::-1]
