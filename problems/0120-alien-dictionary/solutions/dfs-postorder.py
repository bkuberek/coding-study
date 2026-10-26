ON_PATH, DONE = 1, 2


def alien_order(words: list[str]) -> str:
    after: dict[str, set[str]] = {letter: set() for word in words for letter in word}
    for first, second in zip(words, words[1:]):
        for a, b in zip(first, second):
            if a != b:
                after[a].add(b)
                break
        else:
            if len(first) > len(second):
                return ""  # a word placed before its own proper prefix
    state: dict[str, int] = {}
    finished: list[str] = []  # each letter lands here after every letter that must follow it

    def visit(letter: str) -> bool:
        """Emit everything after letter, then letter; False if a rule loops back."""
        state[letter] = ON_PATH
        for target in after[letter]:
            if state.get(target) == ON_PATH:
                return False
            if target not in state and not visit(target):
                return False
        state[letter] = DONE
        finished.append(letter)
        return True

    for letter in after:
        if letter not in state and not visit(letter):
            return ""
    return "".join(reversed(finished))
