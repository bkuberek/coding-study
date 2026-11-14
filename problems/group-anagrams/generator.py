"""Seeded inputs for group-anagrams: `n` words in about n/2 groups.

Each group starts from a random base word of 1 to 8 letters (now and then the empty word)
and holds 1 to 3 shuffles of it; the words of all groups are then shuffled together. Bases
are random, so two groups occasionally share a key and merge, which is fine because expected
values come from a reference.

With about n/2 groups, a linear search over the group keys compares on the order of n^2/8
keys at every seed, while the hash-map approaches do O(k) work per word.
"""

import random
import string

MIN_WORDS = 1
MAX_WORDS = 10**4
MAX_WORD_LENGTH = 100
GENERATED_MAX_LENGTH = 8
MAX_GROUP_SIZE = 3
EMPTY_WORD_PROBABILITY = 0.02


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_WORDS), MAX_WORDS)
    words: list[str] = []
    while len(words) < count:
        base = _base_word(rng)
        for _ in range(min(rng.randint(1, MAX_GROUP_SIZE), count - len(words))):
            letters = list(base)
            rng.shuffle(letters)
            words.append("".join(letters))
    rng.shuffle(words)
    return {"strs": words}


def _base_word(rng: random.Random) -> str:
    if rng.random() < EMPTY_WORD_PROBABILITY:
        return ""
    return "".join(rng.choices(string.ascii_lowercase, k=rng.randint(1, GENERATED_MAX_LENGTH)))


def validate(case_input: dict) -> None:
    words = case_input["strs"]
    assert MIN_WORDS <= len(words) <= MAX_WORDS, "word count out of range"
    for word in words:
        assert len(word) <= MAX_WORD_LENGTH, "word too long"
        assert all("a" <= letter <= "z" for letter in word), "non-lowercase letter"
