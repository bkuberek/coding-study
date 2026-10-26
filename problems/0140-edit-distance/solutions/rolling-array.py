def min_distance(word1: str, word2: str) -> int:
    # The distance is symmetric (insertions and deletions swap roles), so let the rows run
    # along the shorter word.
    longer, shorter = (word1, word2) if len(word1) >= len(word2) else (word2, word1)
    # previous[j] is the distance between longer[:i - 1] and shorter[:j].
    previous = list(range(len(shorter) + 1))
    for i, character in enumerate(longer, start=1):
        current = [i] + [0] * len(shorter)
        for j, other in enumerate(shorter, start=1):
            if character == other:
                current[j] = previous[j - 1]
            else:
                current[j] = 1 + min(previous[j], current[j - 1], previous[j - 1])
        previous = current
    return previous[-1]
