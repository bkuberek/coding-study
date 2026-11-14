ESCAPE = "\\"
TERMINATOR = ","


def encode(strs: list[str]) -> str:
    # Escape the escape character first, or the escapes added for terminators get doubled.
    return "".join(
        text.replace(ESCAPE, ESCAPE + ESCAPE).replace(TERMINATOR, ESCAPE + TERMINATOR) + TERMINATOR
        for text in strs
    )


def decode(encoded: str) -> list[str]:
    strs: list[str] = []
    current: list[str] = []
    escaped = False
    for character in encoded:
        if escaped:
            current.append(character)
            escaped = False
        elif character == ESCAPE:
            escaped = True
        elif character == TERMINATOR:
            strs.append("".join(current))
            current = []
        else:
            current.append(character)
    return strs


def encode_decode(strs: list[str]) -> list[str]:
    return decode(encode(strs))
