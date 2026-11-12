"""How many trie nodes a set of keys needs, compared with the number of letters in the keys.

Keys that share their beginnings share nodes. Keys that share little need a node for most of
their letters, and a node is a whole object with a map of children, much larger than a letter.
"""


def count_nodes(keys: list[str]) -> int:
    root: dict = {}
    nodes = 0
    for key in keys:
        node = root
        for letter in key:
            if letter not in node:
                node[letter] = {}
                nodes += 1
            node = node[letter]
    return nodes


def scattered_keys(count: int, length: int) -> list[str]:
    """Keys of random-looking letters, from a fixed linear congruential generator."""
    state, keys = 12345, []
    for _ in range(count):
        letters = []
        for _ in range(length):
            state = (state * 1103515245 + 12345) % 2**31
            letters.append(chr(ord("a") + (state >> 16) % 26))
        keys.append("".join(letters))
    return keys


datasets = {
    "user0000 to user9999": [f"user{number:04}" for number in range(10_000)],
    "10,000 scattered keys": scattered_keys(10_000, 8),
}
for label, keys in datasets.items():
    letters = sum(len(key) for key in keys)
    nodes = count_nodes(keys)
    print(f"{label}: {letters:,} letters, {nodes:,} nodes, {nodes / letters:.0%} of the letters")
