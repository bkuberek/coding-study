END = "$"  # marks a node where a root ends; never a letter


def replace_words(dictionary: list[str], sentence: str) -> str:
    trie: dict = {}
    for root in dictionary:
        node = trie
        for letter in root:
            node = node.setdefault(letter, {})
        node[END] = True

    def shorten(word: str) -> str:
        node = trie
        for length, letter in enumerate(word):
            if END in node:
                return word[:length]
            node = node.get(letter)
            if node is None:
                return word
        return word

    return " ".join(shorten(word) for word in sentence.split(" "))
