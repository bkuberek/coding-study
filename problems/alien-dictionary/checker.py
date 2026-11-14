"""Accept any alphabet under which the words are sorted, or "" exactly when none exists.

A non-empty answer must hold every letter of the words exactly once and sort the words in
the given order (comparing letter ranks position by position, with a proper prefix first).
An empty answer is accepted only if no alphabet works, which the checker decides with its
own topological sort over the rules read from neighboring words.
"""

from collections import deque


def _some_alphabet(words: list[str]) -> str | None:
    letters = sorted(set("".join(words)))
    after: dict[str, set[str]] = {letter: set() for letter in letters}
    for first, second in zip(words, words[1:]):
        for a, b in zip(first, second):
            if a != b:
                after[a].add(b)
                break
        else:
            if len(first) > len(second):
                return None
    waiting = {letter: 0 for letter in letters}
    for targets in after.values():
        for letter in targets:
            waiting[letter] += 1
    ready = deque(letter for letter in letters if waiting[letter] == 0)
    order: list[str] = []
    while ready:
        letter = ready.popleft()
        order.append(letter)
        for target in after[letter]:
            waiting[target] -= 1
            if waiting[target] == 0:
                ready.append(target)
    return "".join(order) if len(order) == len(letters) else None


def check(case_input: dict, output: object, expected: object | None) -> str | None:
    words = case_input["words"]
    if not isinstance(output, str):
        return f"expected a string, got {output!r}"[:200]
    if output == "":
        alphabet = _some_alphabet(words)
        if alphabet is not None:
            return f"returned an empty string, but the alphabet {alphabet!r} sorts the words"
        return None
    letters = set("".join(words))
    if len(set(output)) != len(output):
        return f"{output!r} lists a letter more than once"
    if set(output) != letters:
        missing = "".join(sorted(letters - set(output)))
        extra = "".join(sorted(set(output) - letters))
        return f"{output!r} must hold exactly the letters of the words (missing {missing!r}, extra {extra!r})"
    rank = {letter: position for position, letter in enumerate(output)}
    for first, second in zip(words, words[1:]):
        if [rank[letter] for letter in first] > [rank[letter] for letter in second]:
            return f"under {output!r}, {first!r} would sort after {second!r}"
    return None
