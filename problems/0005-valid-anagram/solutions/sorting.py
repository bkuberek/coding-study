def is_anagram(s: str, t: str) -> bool:
    return len(s) == len(t) and sorted(s) == sorted(t)
