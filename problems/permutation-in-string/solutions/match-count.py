def check_inclusion(pattern: str, text: str) -> bool:
    width = len(pattern)
    if width > len(text):
        return False
    surplus = [0] * 26
    for ch in pattern:
        surplus[ord(ch) - 97] -= 1
    balanced = sum(1 for value in surplus if value == 0)

    def shift(letter: int, delta: int) -> None:
        nonlocal balanced
        if surplus[letter] == 0:
            balanced -= 1
        surplus[letter] += delta
        if surplus[letter] == 0:
            balanced += 1

    for right, ch in enumerate(text):
        shift(ord(ch) - 97, 1)
        if right >= width:
            shift(ord(text[right - width]) - 97, -1)
        if balanced == 26:
            return True
    return False
