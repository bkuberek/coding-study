"""Seeded inputs for count-words-by-prefix: n words and n prefixes (each capped at 10^4).

Words are built from a pool of about n / 4 stems of 1 to 8 letters, each extended by 0 to 8
more letters (20 at most), so many words share long beginnings and the counts are far from
zero. Below 100 words, which covers the oracle's inputs, half of the inputs use only the
letters `abc`. Half of the prefixes are cut from a random word (length 1 up to the whole word),
a quarter are a word with one letter added, and a quarter are random strings, so every
count from zero upward occurs.

Comparing each prefix with every word costs W * P comparisons whatever the counts are, since
it never stops early, while the trie reads each letter of the input once.
"""

import random
import string

MAX_COUNT = 10**4
MAX_LENGTH = 20
STEM_LENGTH = 8
TAIL_LENGTH = 8
SMALL_INPUT = 100


def _text(rng: random.Random, alphabet: str, longest: int) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(1, longest)))


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_COUNT)
    alphabet = "abc" if count < SMALL_INPUT and rng.random() < 0.5 else string.ascii_lowercase
    stems = [_text(rng, alphabet, STEM_LENGTH) for _ in range(max(1, count // 4))]
    words = []
    for _ in range(count):
        tail = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, TAIL_LENGTH)))
        words.append((rng.choice(stems) + tail)[:MAX_LENGTH])
    prefixes = []
    for _ in range(count):
        roll = rng.random()
        if roll < 0.5:
            word = rng.choice(words)
            prefixes.append(word[: rng.randint(1, len(word))])
        elif roll < 0.75:
            prefixes.append((rng.choice(words) + rng.choice(alphabet))[:MAX_LENGTH])
        else:
            prefixes.append(_text(rng, alphabet, MAX_LENGTH))
    return {"words": words, "prefixes": prefixes}


def validate(case_input: dict) -> None:
    words, prefixes = case_input["words"], case_input["prefixes"]
    assert 1 <= len(words) <= MAX_COUNT, "word count out of range"
    assert 1 <= len(prefixes) <= MAX_COUNT, "prefix count out of range"
    for text in words + prefixes:
        assert 1 <= len(text) <= MAX_LENGTH, "length out of range"
        assert all("a" <= letter <= "z" for letter in text), "only lowercase letters"
