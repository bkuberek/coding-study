ALPHABET_SIZE = 26
SHOWN = 3


class _Node:
    __slots__ = ("children", "smallest")

    def __init__(self) -> None:
        self.children: list[_Node | None] = [None] * ALPHABET_SIZE
        self.smallest: list[str] = []


def suggested_products(products: list[str], search_word: str) -> list[list[str]]:
    root = _Node()
    # Inserting in sorted order means each node's first three products are its smallest.
    for product in sorted(products):
        node = root
        for letter in product:
            index = ord(letter) - ord("a")
            child = node.children[index]
            if child is None:
                child = node.children[index] = _Node()
            node = child
            if len(node.smallest) < SHOWN:
                node.smallest.append(product)
    suggestions: list[list[str]] = []
    cursor: _Node | None = root
    for letter in search_word:
        cursor = cursor.children[ord(letter) - ord("a")] if cursor is not None else None
        suggestions.append(list(cursor.smallest) if cursor is not None else [])
    return suggestions
