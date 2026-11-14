from collections import defaultdict


class WordDictionary:
    def __init__(self) -> None:
        self.by_length: dict[int, set[str]] = defaultdict(set)

    def add_word(self, word: str) -> None:
        self.by_length[len(word)].add(word)

    def search(self, word: str) -> bool:
        candidates = self.by_length[len(word)]
        if "." not in word:
            return word in candidates
        return any(_matches(word, candidate) for candidate in candidates)


def _matches(pattern: str, word: str) -> bool:
    return all(wanted in (".", letter) for wanted, letter in zip(pattern, word))
