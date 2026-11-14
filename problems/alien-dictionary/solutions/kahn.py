from collections import deque


def alien_order(words: list[str]) -> str:
    # after[x] holds the letters that must come after x; every letter of every word is a key.
    after: dict[str, set[str]] = {letter: set() for word in words for letter in word}
    for first, second in zip(words, words[1:]):
        for a, b in zip(first, second):
            if a != b:
                after[a].add(b)
                break
        else:
            if len(first) > len(second):
                return ""  # a word placed before its own proper prefix
    waiting = dict.fromkeys(after, 0)
    for targets in after.values():
        for letter in targets:
            waiting[letter] += 1
    ready = deque(letter for letter in after if waiting[letter] == 0)
    order: list[str] = []
    while ready:
        letter = ready.popleft()
        order.append(letter)
        for target in after[letter]:
            waiting[target] -= 1
            if waiting[target] == 0:
                ready.append(target)
    return "".join(order) if len(order) == len(after) else ""
