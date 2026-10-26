END = "$"


def word_break(s: str, word_dict: list[str]) -> bool:
    # A trie of nested dicts; the END key marks a node where a word finishes.
    root: dict = {}
    for word in word_dict:
        node = root
        for letter in word:
            node = node.setdefault(letter, {})
        node[END] = True

    # reachable[i] is True when the prefix s[:i] can be split into dictionary words.
    reachable = [False] * (len(s) + 1)
    reachable[0] = True
    for start in range(len(s)):
        if not reachable[start]:
            continue
        node = root
        for position in range(start, len(s)):
            node = node.get(s[position])
            if node is None:
                break
            if END in node:
                reachable[position + 1] = True
    return reachable[len(s)]
