ALPHABET_SIZE = 26


class _Node:
    __slots__ = ("children", "passing")

    def __init__(self) -> None:
        self.children: list[_Node | None] = [None] * ALPHABET_SIZE
        self.passing = 0  # how many words go through this node


def count_by_prefix(words: list[str], prefixes: list[str]) -> list[int]:
    root = _Node()
    for word in words:
        node = root
        for letter in word:
            slot = ord(letter) - ord("a")
            child = node.children[slot]
            if child is None:
                child = node.children[slot] = _Node()
            child.passing += 1
            node = child

    counts: list[int] = []
    for prefix in prefixes:
        node = root
        for letter in prefix:
            child = node.children[ord(letter) - ord("a")]
            if child is None:
                counts.append(0)  # the path breaks off: no word begins with this prefix
                break
            node = child
        else:
            counts.append(node.passing)
    return counts
