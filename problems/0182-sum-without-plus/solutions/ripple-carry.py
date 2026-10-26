WORD_BITS = 32
SIGN_BIT = 1 << (WORD_BITS - 1)
MASK = (1 << WORD_BITS) - 1


def get_sum(a: int, b: int) -> int:
    # Python ints are unbounded; masking gives the 32-bit two's complement pattern.
    a, b = a & MASK, b & MASK
    result = carry = 0
    for position in range(WORD_BITS):
        x, y = (a >> position) & 1, (b >> position) & 1
        result |= (x ^ y ^ carry) << position
        carry = (x & y) | (carry & (x ^ y))  # carry out: at least two of the three bits
    # A set sign bit means a negative value: flip the low 32 bits back and invert.
    return result if not result & SIGN_BIT else ~(result ^ MASK)
