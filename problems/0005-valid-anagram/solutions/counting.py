ALPHABET_SIZE = 26
BASE = ord("a")


def is_anagram(s: str, t: str) -> bool:
    if len(s) != len(t):
        return False
    counts = [0] * ALPHABET_SIZE
    for letter in s:
        counts[ord(letter) - BASE] += 1
    for letter in t:
        index = ord(letter) - BASE
        counts[index] -= 1
        if counts[index] < 0:
            return False
    return True
