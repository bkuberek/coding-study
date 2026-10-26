MARKER = "#"


def encode(strs: list[str]) -> str:
    return "".join(f"{len(text)}{MARKER}{text}" for text in strs)


def decode(encoded: str) -> list[str]:
    strs: list[str] = []
    position = 0
    while position < len(encoded):
        # A length has only digits, so the first marker after it ends the length.
        marker = encoded.index(MARKER, position)
        start = marker + 1
        end = start + int(encoded[position:marker])
        strs.append(encoded[start:end])
        position = end
    return strs


def encode_decode(strs: list[str]) -> list[str]:
    return decode(encode(strs))
