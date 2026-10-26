ALPHABET_SIZE = 26


class _Node:
    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: list[_Node | None] = [None] * ALPHABET_SIZE
        self.is_word = False


class WordDictionary:
    def __init__(self) -> None:
        self.root = _Node()

    def add_word(self, word: str) -> None:
        node = self.root
        for letter in word:
            index = ord(letter) - ord("a")
            child = node.children[index]
            if child is None:
                child = node.children[index] = _Node()
            node = child
        node.is_word = True

    def search(self, word: str) -> bool:
        def matches_from(node: _Node, position: int) -> bool:
            """Does some stored word continue from `node` the way word[position:] says?"""
            for at in range(position, len(word)):
                if word[at] == ".":
                    return any(child is not None and matches_from(child, at + 1) for child in node.children)
                child = node.children[ord(word[at]) - ord("a")]
                if child is None:
                    return False
                node = child
            return node.is_word

        return matches_from(self.root, 0)
