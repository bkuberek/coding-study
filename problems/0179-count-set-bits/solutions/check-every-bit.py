WORD_BITS = 32


def hamming_weight(n: int) -> int:
    return sum((n >> position) & 1 for position in range(WORD_BITS))
