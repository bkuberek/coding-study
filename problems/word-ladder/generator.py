"""Seeded dictionaries for word-ladder.

`n` is the dictionary size (capped at 5000). Words have a length L between 3 and 6 (1 to 3
when n is tiny) over the first k letters of the alphabet, with k chosen so that the k^L
possible words outnumber the dictionary by a random factor between 2 and 20: dense
dictionaries make every word reachable, sparse ones leave gaps. A random walk of one-letter
changes from beginWord supplies a guaranteed ladder (shortcuts may make the answer shorter);
the rest of the dictionary is random words. Some inputs drop endWord from the dictionary or
pick an unrelated endWord, so the answer is often 0 there; some add beginWord itself to the
dictionary, which must not change the answer.

From SPLIT_FROM words on (the bench ladder), every input has one shape instead: words of
length SPLIT_LENGTH, split into two halves that share no word one letter apart (the first two
letters come from a-m in one half and from n-z in the other). Each half is the trail of a
random walk of one-letter changes, from beginWord in one half and from endWord in the other,
so endWord is never reachable and the answer is 0. Every search then explores a whole half
before it gives up, and the list-scanning search compares each word it reaches with the n / 2
words of the other half that stay unvisited, so it grows as n^2 on every seed.
"""

import random
import string

MAX_WORDS = 5000
MAX_WALK = 60
SPLIT_FROM = 100
SPLIT_LENGTH = 5


def _random_word(rng: random.Random, letters: str, length: int) -> str:
    return "".join(rng.choice(letters) for _ in range(length))


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_WORDS)
    if count >= SPLIT_FROM:
        return _split(rng, count)
    length = rng.randint(1, 3) if count < 8 else rng.randint(3, 6)
    room = rng.uniform(2, 20) * (count + 1)
    alphabet = 2
    while alphabet < 26 and alphabet**length < room:
        alphabet += 1
    letters = string.ascii_lowercase[:alphabet]
    # Leave room for beginWord outside the dictionary.
    count = min(count, alphabet**length - 1)

    begin = _random_word(rng, letters, length)
    walk = [begin]
    seen = {begin}
    for _ in range(rng.randint(1, MAX_WALK)):
        current = list(walk[-1])
        position = rng.randrange(length)
        current[position] = rng.choice([ch for ch in letters if ch != current[position]])
        word = "".join(current)
        if word not in seen:
            seen.add(word)
            walk.append(word)
    words = walk[1 : count + 1]
    taken = set(words) | {begin}
    while len(words) < count:
        word = _random_word(rng, letters, length)
        if word not in taken:
            taken.add(word)
            words.append(word)

    end = words[len(walk[1 : count + 1]) - 1] if len(walk) > 1 else words[-1]
    kind = rng.random()
    if kind < 0.08 and len(words) > 1:
        words.remove(end)
    elif kind < 0.16:
        end = rng.choice(words)
    if rng.random() < 0.3 and len(words) < MAX_WORDS:
        words.append(begin)
    rng.shuffle(words)
    return {"beginWord": begin, "endWord": end, "wordList": words}


def _split(rng: random.Random, count: int) -> dict:
    halves = (string.ascii_lowercase[:13], string.ascii_lowercase[13:])
    trails = [_trail(rng, head, count // 2 + 1) for head in halves]
    begin, end = trails[0][0], trails[1][0]
    words = trails[0][1:] + trails[1][: count - count // 2]
    rng.shuffle(words)
    return {"beginWord": begin, "endWord": end, "wordList": words}


def _trail(rng: random.Random, head: str, size: int) -> list[str]:
    """Distinct words visited by a random walk; the first two letters stay within head."""
    tail = string.ascii_lowercase
    current = [rng.choice(head if position < 2 else tail) for position in range(SPLIT_LENGTH)]
    trail = ["".join(current)]
    seen = set(trail)
    while len(trail) < size:
        position = rng.randrange(SPLIT_LENGTH)
        letters = head if position < 2 else tail
        current[position] = rng.choice([ch for ch in letters if ch != current[position]])
        word = "".join(current)
        if word not in seen:
            seen.add(word)
            trail.append(word)
    return trail


def validate(case_input: dict) -> None:
    begin, end, words = case_input["beginWord"], case_input["endWord"], case_input["wordList"]
    assert 1 <= len(begin) <= 10, "word length out of range"
    assert len(end) == len(begin) and all(len(word) == len(begin) for word in words), "lengths differ"
    assert 1 <= len(words) <= MAX_WORDS, "dictionary size out of range"
    assert len(set(words)) == len(words), "dictionary has repeats"
    assert begin != end, "begin equals end"
    for word in [begin, end, *words]:
        assert all(ch in string.ascii_lowercase for ch in word), "not lowercase letters"
