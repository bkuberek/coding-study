"""Seeded operation sequences for implement-trie.

`n` is the number of calls after the constructor: `insert` 40%, `search` 30%, `startsWith` 30%.
Below 100 calls, which covers the oracle's inputs, half of the inputs use the letters `abc`
with words of 1 to 6 letters, so prefixes are shared heavily; the others, and every input from
100 calls on, use all 26 letters with words of 1 to 12 letters. Half of the queries are built
from an earlier word (the word itself, a prefix of it, or the word with one letter added), the
rest are random strings.

Scanning every stored word for each `startsWith` makes the call sequence quadratic in n, while
the trie stays linear. The scan stops at the first word with the prefix, and with three
letters almost every prefix has one among the first few words, which would make the scan
nearly free on some seeds of the ladder and quadratic on others; with 26 letters a random
prefix of three or more letters rarely matches, so the scan reads the stored words at every
seed.
"""

import random
import string

MAX_CALLS = 10**4
MAX_LENGTH = 20
CALL_WEIGHTS = (("insert", 0.4), ("search", 0.3), ("startsWith", 0.3))
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    if rng.random() < 0.5 and calls < UNIFORM_FROM:
        alphabet, longest = "abc", 6
    else:
        alphabet, longest = string.ascii_lowercase, 12
    names = [name for name, _ in CALL_WEIGHTS]
    weights = [weight for _, weight in CALL_WEIGHTS]
    words: list[str] = []
    ops: list[str] = ["Trie"]
    args: list[list[str]] = [[]]
    for _ in range(calls):
        op = rng.choices(names, weights)[0]
        if op == "insert" or not words or rng.random() < 0.5:
            text = _random_word(rng, alphabet, longest)
        else:
            text = _derived(rng, rng.choice(words), alphabet)
        if op == "insert":
            words.append(text)
        ops.append(op)
        args.append([text])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "Trie" and args[0] == [], "the first op must be the constructor"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert op in ("insert", "search", "startsWith") and len(arguments) == 1, f"bad call {op}"
        text = arguments[0]
        assert 1 <= len(text) <= MAX_LENGTH, "length out of range"
        assert all("a" <= letter <= "z" for letter in text), "only lowercase letters"


def _random_word(rng: random.Random, alphabet: str, longest: int) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(1, longest)))


def _derived(rng: random.Random, word: str, alphabet: str) -> str:
    roll = rng.random()
    if roll < 0.4:
        return word
    if roll < 0.8:
        return word[: rng.randint(1, len(word))]
    return (word + rng.choice(alphabet))[:MAX_LENGTH]
