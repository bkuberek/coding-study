OPENER_OF = {")": "(", "]": "[", "}": "{"}


def is_valid(s: str) -> bool:
    open_brackets: list[str] = []
    for character in s:
        opener = OPENER_OF.get(character)
        if opener is None:
            open_brackets.append(character)
        elif not open_brackets or open_brackets.pop() != opener:
            return False
    return not open_brackets
