"""Seeded inputs for alien-dictionary: words sorted by a hidden alphabet, sometimes spoiled.

There are n words (capped at 1000) over a hidden random order of 1 to 26 letters, each 1 to
20 letters long, sorted by that order. Then, with probability 1/4, two neighboring words are
swapped, which may or may not leave some alphabet that explains the list; with probability
1/10, a word is followed by its own proper prefix, which no alphabet can sort. The checker
decides which answers are valid, so the generator does not need to know.
"""

import random
import string

MIN_WORDS = 1
MAX_WORDS = 1000
MAX_LENGTH = 20


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_WORDS), MAX_WORDS)
    alphabet = rng.sample(string.ascii_lowercase, rng.randint(1, 26))
    rank = {letter: position for position, letter in enumerate(alphabet)}
    longest = rng.randint(1, MAX_LENGTH)
    words = [
        "".join(rng.choice(alphabet) for _ in range(rng.randint(1, longest))) for _ in range(count)
    ]
    words.sort(key=lambda word: [rank[letter] for letter in word])
    if count >= 2 and rng.random() < 0.25:
        i = rng.randrange(count - 1)
        words[i], words[i + 1] = words[i + 1], words[i]
    if rng.random() < 0.1:
        i = rng.randrange(count)
        if 2 <= len(words[i]):
            words[i + 1 : i + 1] = [words[i][: rng.randint(1, len(words[i]) - 1)]]
            words = words[:MAX_WORDS]
    return {"words": words}


def validate(case_input: dict) -> None:
    words = case_input["words"]
    assert MIN_WORDS <= len(words) <= MAX_WORDS, "word count out of range"
    assert all(1 <= len(word) <= MAX_LENGTH for word in words), "word length out of range"
    assert all(set(word) <= set(string.ascii_lowercase) for word in words), "words must be lowercase"
