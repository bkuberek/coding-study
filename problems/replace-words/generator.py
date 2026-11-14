"""Seeded inputs for replace-words: n words and about n/4 distinct roots.

Roots have 2 to 6 letters; a quarter of them extend an earlier root by 1 to 3 letters, so
the shortest-root rule matters. Half of the words are a root plus 0 to 5 letters, the rest
are random words of 1 to 10 letters. At oracle sizes (30 words or fewer) half of the inputs
use only the letters `abc`, so roots share prefixes heavily; every other input uses all 26
letters. Checking every root against every word costs about n^2 / 4 prefix tests at every
seed, while the trie reads each letter once.
"""

import random
import string

MAX_WORDS = 10**4
MAX_ROOTS = 2000
MAX_WORD_LENGTH = 100
SMALL_UP_TO = 30


def generate(rng: random.Random, n: int) -> dict:
    word_count = min(max(n, 1), MAX_WORDS)
    root_count = min(MAX_ROOTS, max(1, word_count // 4))
    small = word_count <= SMALL_UP_TO and rng.random() < 0.5
    alphabet = "abc" if small else string.ascii_lowercase

    def letters(low: int, high: int) -> str:
        return "".join(rng.choice(alphabet) for _ in range(rng.randint(low, high)))

    roots: list[str] = []
    seen: set[str] = set()
    while len(roots) < root_count:
        if roots and rng.random() < 0.25:
            root = (rng.choice(roots) + letters(1, 3))[:MAX_WORD_LENGTH]
        else:
            root = letters(2, 6)
        if root not in seen:
            seen.add(root)
            roots.append(root)
    words = [
        rng.choice(roots) + letters(0, 5) if rng.random() < 0.5 else letters(1, 10)
        for _ in range(word_count)
    ]
    return {"dictionary": roots, "sentence": " ".join(words)}


def validate(case_input: dict) -> None:
    dictionary, sentence = case_input["dictionary"], case_input["sentence"]
    assert 1 <= len(dictionary) <= MAX_ROOTS, "root count out of range"
    assert len(set(dictionary)) == len(dictionary), "roots must be distinct"
    lowercase = set(string.ascii_lowercase)
    for root in dictionary:
        assert 1 <= len(root) <= MAX_WORD_LENGTH, "root length out of range"
        assert set(root) <= lowercase, "roots use lowercase letters"
    words = sentence.split(" ")
    assert 1 <= len(words) <= MAX_WORDS, "word count out of range"
    for word in words:
        assert 1 <= len(word) <= MAX_WORD_LENGTH, "word length out of range or extra spacing"
        assert set(word) <= lowercase, "words use lowercase letters"
