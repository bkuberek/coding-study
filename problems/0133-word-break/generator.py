"""Seeded inputs for word-break.

`n` is the length of `s`, clamped to 1..2000. Each input draws a small alphabet (2 to 4
letters), so that words overlap and many split points compete, and up to 40 distinct words of
1 to 8 letters (single letters are rare, otherwise almost every text would split). The text is
built from random dictionary words up to about `n` letters; in one input out of three, random
characters are then replaced by other letters of the alphabet, one at a time and at most 20
times, until the text no longer splits. When no word is short enough, the text is random
letters.

From UNIFORM_FROM letters on (the bench ladder), every input has one shape instead: three
letters, exactly 40 words of 2 to 8 letters, and a text that splits. The cost per position
then no longer depends on how many words, how long a longest word or how many letters a seed
happened to draw.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 2000
MAX_WORDS = 40
MAX_WORD_LENGTH = 8
SINGLE_LETTER_SHARE = 0.03
BROKEN_SHARE = 1 / 3
WORD_ATTEMPTS = 1000
BREAK_ATTEMPTS = 20
UNIFORM_FROM = 100
UNIFORM_LETTERS = 3


def _word_length(rng: random.Random) -> int:
    if rng.random() < SINGLE_LETTER_SHARE:
        return 1
    return rng.randint(2, MAX_WORD_LENGTH)


def _dictionary(rng: random.Random, letters: list[str], uniform: bool) -> list[str]:
    target = MAX_WORDS if uniform else rng.randint(1, MAX_WORDS)
    words: set[str] = set()
    for _ in range(WORD_ATTEMPTS):
        if len(words) == target:
            break
        size = rng.randint(2, MAX_WORD_LENGTH) if uniform else _word_length(rng)
        words.add("".join(rng.choice(letters) for _ in range(size)))
    ordered = sorted(words)
    rng.shuffle(ordered)
    return ordered


def _text(rng: random.Random, words: list[str], length: int, letters: list[str]) -> str:
    shortest = min(words, key=len)
    pieces: list[str] = []
    total = 0
    while total < length:
        word = rng.choice(words)
        if total + len(word) > length:
            word = shortest
            if total + len(word) > length:
                break
        pieces.append(word)
        total += len(word)
    if not pieces:
        return "".join(rng.choice(letters) for _ in range(length))
    return "".join(pieces)


def _splits(s: str, words: list[str]) -> bool:
    vocabulary = set(words)
    ok = [True] + [False] * len(s)
    for end in range(1, len(s) + 1):
        ok[end] = any(
            ok[start] and s[start:end] in vocabulary
            for start in range(max(0, end - MAX_WORD_LENGTH), end)
        )
    return ok[len(s)]


def _break(rng: random.Random, s: str, words: list[str], letters: list[str]) -> str:
    """Replace one character at a time until the text no longer splits (bounded attempts)."""
    for _ in range(BREAK_ATTEMPTS):
        position = rng.randrange(len(s))
        s = s[:position] + rng.choice(letters) + s[position + 1 :]
        if not _splits(s, words):
            break
    return s


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    uniform = length >= UNIFORM_FROM
    letters = rng.sample(string.ascii_lowercase, UNIFORM_LETTERS if uniform else rng.randint(2, 4))
    words = _dictionary(rng, letters, uniform)
    s = _text(rng, words, length, letters)
    if not uniform and rng.random() < BROKEN_SHARE:
        s = _break(rng, s, words, letters)
    return {"s": s, "wordDict": words}


def validate(case_input: dict) -> None:
    s, words = case_input["s"], case_input["wordDict"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "text length out of range"
    assert 1 <= len(words) <= 1000, "dictionary size out of range"
    assert len(set(words)) == len(words), "dictionary words are not distinct"
    assert all(1 <= len(word) <= 20 for word in words), "word length out of range"
    lowercase = set(string.ascii_lowercase)
    assert set(s) <= lowercase, "text must be lowercase letters"
    assert all(set(word) <= lowercase for word in words), "words must be lowercase letters"
