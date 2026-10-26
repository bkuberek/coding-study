def longest_common_subsequence(text1: str, text2: str) -> int:
    # The answer is symmetric, so let the rows run along the shorter string.
    longer, shorter = (text1, text2) if len(text1) >= len(text2) else (text2, text1)
    # previous[j] is the answer for the prefixes longer[:i - 1] and shorter[:j].
    previous = [0] * (len(shorter) + 1)
    for character in longer:
        current = [0] * (len(shorter) + 1)
        for j, other in enumerate(shorter, start=1):
            if character == other:
                current[j] = previous[j - 1] + 1
            else:
                current[j] = max(previous[j], current[j - 1])
        previous = current
    return previous[-1]
