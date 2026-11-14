def check_inclusion(pattern: str, text: str) -> bool:
    width = len(pattern)
    target = sorted(pattern)
    for start in range(len(text) - width + 1):
        if sorted(text[start : start + width]) == target:
            return True
    return False
