"""Seeded inputs for regex-matching: s of length n and a pattern built from s.

s has n letters (at most 1000) over an alphabet of 2 to 4 letters. The pattern is built
by walking s and emitting a token for each piece: a literal letter, `.`, `x*` for a run of
the letter x, or `.*` for a chunk of 1 to 5 letters; now and then an extra `y*` that matches
nothing is inserted. That pattern matches s and has about as many characters as s (it is
cut back token by token if it exceeds 1000). On half of the seeds one literal letter of the
pattern is changed, or a literal letter is appended, which usually breaks the match only
after much of the table has been explored. Every table approach fills
(len(s) + 1)(len(p) + 1) cells.

From WORST_FROM letters on (the bench ladder), every input is a worst case for the top-down
search instead: s over "ab" and a pattern of `.*` tokens about as long as s, ended by a `c`
that no letter of s matches. Every `.*` can take any number of letters, so the search reaches
every pair of a position in s and a token before it fails; a pattern that matches lets it stop
at the first success, after a share of the pairs that varies from seed to seed.
"""

import random

MAX_LENGTH = 1000
ALPHABETS = ("ab", "abc", "abcd")
EMPTY_STAR_PROBABILITY = 0.15
WORST_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 0), MAX_LENGTH)
    if length >= WORST_FROM:
        return {"s": "".join(rng.choices("ab", k=length)), "p": ".*" * ((length - 1) // 2) + "c"}
    letters = rng.choice(ALPHABETS)
    s = "".join(rng.choices(letters, k=length))
    tokens = _tokens(rng, s, letters)
    if rng.random() < 0.5:
        _break(rng, tokens, letters)
    while len("".join(tokens)) > MAX_LENGTH:
        tokens.pop()
    return {"s": s, "p": "".join(tokens) or rng.choice(letters) + "*"}


def _tokens(rng: random.Random, s: str, letters: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(s):
        roll = rng.random()
        if roll < 0.35:
            tokens.append(s[i])
            i += 1
        elif roll < 0.5:
            tokens.append(".")
            i += 1
        elif roll < 0.8:
            end = i + 1
            while end < len(s) and s[end] == s[i] and rng.random() < 0.8:
                end += 1
            tokens.append(s[i] + "*")
            i = end
        else:
            tokens.append(".*")
            i = min(len(s), i + rng.randint(1, 5))
        if rng.random() < EMPTY_STAR_PROBABILITY:
            tokens.append(rng.choice(letters) + "*")
    return tokens


def _break(rng: random.Random, tokens: list[str], letters: str) -> None:
    literals = [index for index, token in enumerate(tokens) if len(token) == 1 and token != "."]
    if literals and rng.random() < 0.7:
        index = rng.choice(literals)
        tokens[index] = rng.choice([letter for letter in letters if letter != tokens[index]])
    else:
        tokens.append(rng.choice(letters))


def validate(case_input: dict) -> None:
    s, p = case_input["s"], case_input["p"]
    assert 0 <= len(s) <= MAX_LENGTH, "s length out of range"
    assert 1 <= len(p) <= MAX_LENGTH, "p length out of range"
    assert all("a" <= character <= "z" for character in s), "s must be lowercase letters"
    assert all("a" <= character <= "z" or character in ".*" for character in p), "bad pattern character"
    for index, character in enumerate(p):
        if character == "*":
            assert index > 0 and p[index - 1] != "*", "every star needs a letter or dot before it"
