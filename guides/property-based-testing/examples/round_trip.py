"""A property, a generator, a runner and a shrinker, in one short program.

The property: decoding what run-length encoding produced gives back the original text. The
decoder has a bug that no short example shows: it reads a count as a single digit. The runner
finds a failing text, and the shrinker cuts it down to one that shows the bug at a glance.
"""

import random


def encode(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and text[j] == text[i]:
            j += 1
        out.append(f"{j - i}{text[i]}")
        i = j
    return "".join(out)


def decode(code: str) -> str:
    out = []
    for count, letter in zip(code[0::2], code[1::2]):  # bug: assumes every count is one digit
        out.append(letter * int(count))
    return "".join(out)


def round_trips(text: str) -> bool:
    try:
        return decode(encode(text)) == text
    except (ValueError, IndexError):
        return False


def below(rng: random.Random, n: int) -> int:
    return int(rng.random() * n)


def runs_of_letters(rng: random.Random) -> str:
    """The generator: up to 4 runs, each of 1 to 12 copies of a or b."""
    return "".join("ab"[below(rng, 2)] * (1 + below(rng, 12)) for _ in range(below(rng, 5)))


def candidates(text: str):
    """Simpler texts: drop one letter, then turn one b into a."""
    for i in range(len(text)):
        yield text[:i] + text[i + 1:]
    for i, letter in enumerate(text):
        if letter == "b":
            yield text[:i] + "a" + text[i + 1:]


def shrink(text: str) -> list[str]:
    """Greedy: move to the first simpler text that still fails, until none does."""
    path = [text]
    while True:
        simpler = next((c for c in candidates(path[-1]) if not round_trips(c)), None)
        if simpler is None:
            return path
        path.append(simpler)


SEED = 2093
rng = random.Random(SEED)
for run in range(1, 101):
    text = runs_of_letters(rng)
    if not round_trips(text):
        print(f"seed {SEED}, run {run}: fails on {text!r} ({len(text)} letters)")
        path = shrink(text)
        print(f"shrunk in {len(path) - 1} steps to {path[-1]!r}: encoded {encode(path[-1])!r}, "
              f"decoded {decode(encode(path[-1]))!r}")
        break
else:
    print("passed 100 runs")
