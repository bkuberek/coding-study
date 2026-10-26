def decode_string(s: str) -> str:
    # For every open group: its repeat count and the text built before its "[".
    counts: list[int] = []
    outer_texts: list[list[str]] = []
    current: list[str] = []
    count = 0
    for character in s:
        if character.isdigit():
            count = count * 10 + int(character)
        elif character == "[":
            counts.append(count)
            outer_texts.append(current)
            current = []
            count = 0
        elif character == "]":
            outer = outer_texts.pop()
            outer.append("".join(current) * counts.pop())
            current = outer
        else:
            current.append(character)
    return "".join(current)
