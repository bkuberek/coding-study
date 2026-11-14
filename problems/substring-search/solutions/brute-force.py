def find_all_occurrences(text: str, pattern: str) -> list[int]:
    found = []
    for start in range(len(text) - len(pattern) + 1):
        offset = 0
        while offset < len(pattern) and text[start + offset] == pattern[offset]:
            offset += 1
        if offset == len(pattern):
            found.append(start)
    return found
