"""Seeded operation sequences for wildcard-word-dictionary.

`n` is the number of calls after the constructor: `addWord` 45%, `search` 55%. Two thirds of
the patterns are built from an earlier word, and a third of those also get one letter changed
or one letter added or removed; the rest are random patterns.

Below 100 calls, which covers the oracle's inputs, half of the inputs use the letters `abcd`
with words of 1 to 5 letters, so many patterns match; the others use all 26 letters with words
of 1 to 10 letters; every pattern has 0 to 3 dots.

From 100 calls on, the sizes the ladder times, every input uses all 26 letters and every
pattern has exactly one dot. Each dotted search then makes the word scan compare the pattern
with the stored words of its length, which keeps growing because words over 26 letters rarely
repeat (with `abcd` they stop growing once every short word is stored), so the scan stays
quadratic over the call sequence. One dot also bounds the trie search by 26 branches: with
three leading dots it visits every stored prefix of three letters, and while fewer than 26^3
words are stored that share grows with n.
"""

import random
import string

MAX_CALLS = 10**4
MAX_LENGTH = 20
MAX_DOTS = 3
ADD_PROBABILITY = 0.45
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    uniform = calls >= UNIFORM_FROM
    if rng.random() < 0.5 and not uniform:
        alphabet, longest = "abcd", 5
    else:
        alphabet, longest = string.ascii_lowercase, 10
    words: list[str] = []
    ops: list[str] = ["WordDictionary"]
    args: list[list[str]] = [[]]
    for _ in range(calls):
        if rng.random() < ADD_PROBABILITY:
            word = _random_word(rng, alphabet, longest)
            words.append(word)
            ops.append("addWord")
            args.append([word])
            continue
        dots = 1 if uniform else rng.randint(0, MAX_DOTS)
        if words and rng.random() < 2 / 3:
            base = _derived(rng, rng.choice(words), alphabet)
        else:
            base = _random_word(rng, alphabet, longest)
        ops.append("search")
        args.append([_with_dots(rng, base, dots)])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "WordDictionary" and args[0] == [], "the first op must be the constructor"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert op in ("addWord", "search") and len(arguments) == 1, f"bad call {op}"
        text = arguments[0]
        assert 1 <= len(text) <= MAX_LENGTH, "length out of range"
        if op == "addWord":
            assert all("a" <= letter <= "z" for letter in text), "words are lowercase letters"
        else:
            assert all(letter == "." or "a" <= letter <= "z" for letter in text), "bad pattern character"
            assert text.count(".") <= MAX_DOTS, "too many dots"


def _random_word(rng: random.Random, alphabet: str, longest: int) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(1, longest)))


def _derived(rng: random.Random, word: str, alphabet: str) -> str:
    letters = list(word)
    if rng.random() < 1 / 3:
        roll = rng.random()
        position = rng.randrange(len(letters))
        if roll < 0.5:
            letters[position] = rng.choice(alphabet)
        elif roll < 0.75 and len(letters) < MAX_LENGTH:
            letters.insert(position, rng.choice(alphabet))
        elif len(letters) > 1:
            del letters[position]
    return "".join(letters)


def _with_dots(rng: random.Random, word: str, dots: int) -> str:
    letters = list(word)
    for position in rng.sample(range(len(letters)), min(len(letters), dots)):
        letters[position] = "."
    return "".join(letters)
