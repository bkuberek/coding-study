BASE = 131
MODULUS = 1_000_000_007


def find_all_occurrences(text: str, pattern: str) -> list[int]:
    window_size = len(pattern)
    if window_size > len(text):
        return []
    # BASE ** (window_size - 1) is the weight of the letter that leaves the window.
    leaving_weight = pow(BASE, window_size - 1, MODULUS)
    target = 0
    window = 0
    for i in range(window_size):
        target = (target * BASE + ord(pattern[i])) % MODULUS
        window = (window * BASE + ord(text[i])) % MODULUS
    found = []
    for start in range(len(text) - window_size + 1):
        if window == target and text.startswith(pattern, start):
            found.append(start)
        if start + window_size < len(text):
            window = ((window - ord(text[start]) * leaving_weight) * BASE + ord(text[start + window_size])) % MODULUS
    return found
