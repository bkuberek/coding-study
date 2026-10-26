MASK = 0xFFFFFFFF
SIGN_BIT = 0x80000000


def get_sum(a: int, b: int) -> int:
    # Work on the 32-bit patterns; without the mask a negative carry never dies out.
    a, b = a & MASK, b & MASK
    while b:
        carry = ((a & b) << 1) & MASK
        a = a ^ b  # the sum of every column, ignoring carries
        b = carry
    # A set sign bit means a negative value: flip the low 32 bits back and invert.
    return a if not a & SIGN_BIT else ~(a ^ MASK)
