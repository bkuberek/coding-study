ALPHABET_SIZE = 26
BASE = ord("a")


def group_anagrams(strs: list[str]) -> list[list[str]]:
    groups: dict[tuple[int, ...], list[str]] = {}
    for word in strs:
        counts = [0] * ALPHABET_SIZE
        for letter in word:
            counts[ord(letter) - BASE] += 1
        # Lists are not hashable; a tuple of the 26 counts is.
        groups.setdefault(tuple(counts), []).append(word)
    return list(groups.values())
