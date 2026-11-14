def min_remove_to_make_valid(s: str) -> str:
    characters = list(s)
    open_positions: list[int] = []
    for position, character in enumerate(characters):
        if character == "(":
            open_positions.append(position)
        elif character == ")":
            if open_positions:
                open_positions.pop()  # matches the most recent unmatched opener
            else:
                characters[position] = ""  # nothing open: this closer can never match
    for position in open_positions:
        characters[position] = ""  # openers that were never closed
    return "".join(characters)
