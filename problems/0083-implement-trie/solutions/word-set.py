class Trie:
    def __init__(self) -> None:
        self.words: set[str] = set()

    def insert(self, word: str) -> None:
        self.words.add(word)

    def search(self, word: str) -> bool:
        return word in self.words

    def starts_with(self, prefix: str) -> bool:
        return any(word.startswith(prefix) for word in self.words)
