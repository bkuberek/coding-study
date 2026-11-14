def check_inclusion(pattern: str, text: str) -> bool:
    width = len(pattern)
    if width > len(text):
        return False
    need = [0] * 26
    window = [0] * 26
    for ch in pattern:
        need[ord(ch) - 97] += 1
    for right, ch in enumerate(text):
        window[ord(ch) - 97] += 1
        if right >= width:
            window[ord(text[right - width]) - 97] -= 1
        if right >= width - 1 and window == need:
            return True
    return False
