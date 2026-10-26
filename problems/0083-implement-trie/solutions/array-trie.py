ALPHABET_SIZE = 26


class _Node:
    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: list[_Node | None] = [None] * ALPHABET_SIZE
        self.is_word = False


class Trie:
    def __init__(self) -> None:
        self.root = _Node()

    def insert(self, word: str) -> None:
        node = self.root
        for letter in word:
            index = ord(letter) - ord("a")
            child = node.children[index]
            if child is None:
                child = node.children[index] = _Node()
            node = child
        node.is_word = True

    def search(self, word: str) -> bool:
        node = self._walk(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        return self._walk(prefix) is not None

    def _walk(self, text: str) -> _Node | None:
        """The node at the end of the path spelled by `text`, or None if the path breaks off."""
        node: _Node | None = self.root
        for letter in text:
            node = node.children[ord(letter) - ord("a")]
            if node is None:
                return None
        return node
