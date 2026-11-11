"""A symbol table: each distinct word gets a small, dense integer id, in O(1) both ways.

The map turns a word into its id; the array turns an id back into its word. Because ids run from
0 without gaps, any data about the words can live in plain arrays indexed by id.
"""


class SymbolTable:
    def __init__(self) -> None:
        self.ids: dict[str, int] = {}  # word -> id
        self.words: list[str] = []  # id -> word

    def intern(self, word: str) -> int:
        """The word's id, assigning the next one the first time the word is seen."""
        known = self.ids.get(word)
        if known is not None:
            return known
        self.ids[word] = len(self.words)
        self.words.append(word)
        return self.ids[word]


symbols = SymbolTable()
text = "to be or not to be that is the question"
ids = [symbols.intern(word) for word in text.split()]
print("ids:", ids)
print("words by id:", symbols.words)

counts = [0] * len(symbols.words)  # per-word data in an array, indexed by id
for word_id in ids:
    counts[word_id] += 1
print("counts by id:", counts)
print("id of 'be':", symbols.ids["be"], "| word with id 4:", symbols.words[4])
