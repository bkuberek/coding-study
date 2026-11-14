def decode_string(s: str) -> str:
    decoded, _ = _decode(s, 0)
    return decoded


def _decode(s: str, position: int) -> tuple[str, int]:
    """Decode from `position` up to the "]" that closes the current group, or to the end.

    Returns the decoded text and the position just after that "]".
    """
    parts: list[str] = []
    count = 0
    while position < len(s):
        character = s[position]
        position += 1
        if character.isdigit():
            count = count * 10 + int(character)
        elif character == "[":
            inner, position = _decode(s, position)
            parts.append(inner * count)
            count = 0
        elif character == "]":
            break
        else:
            parts.append(character)
    return "".join(parts), position
