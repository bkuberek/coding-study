def count_by_prefix(words: list[str], prefixes: list[str]) -> list[int]:
    return [sum(word.startswith(prefix) for word in words) for prefix in prefixes]
