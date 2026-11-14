"""Internal fragmentation: the bytes a block holds beyond the request, under three rounding rules.

Ten requests from an imagined program are rounded up three ways: to a multiple of 16 bytes, to a
power of two, and to one of four classes per power of two (16, 20, 24, 28, then 32, 40, 48, 56,
then 64, 80, ...). The program prints the bytes wasted inside the blocks, and how many distinct
block sizes up to 8192 bytes each rule needs, since an allocator keeps a free list per size.
"""

REQUESTS = [24, 40, 100, 130, 200, 600, 1000, 1500, 3000, 5000]
LIMIT = 8192


def multiple_of_16(size: int) -> int:
    return -(-size // 16) * 16


def power_of_two(size: int) -> int:
    block = 16
    while block < size:
        block *= 2
    return block


def quarter_classes(size: int) -> int:
    """Between 2**k and 2**(k + 1), classes are 2**(k - 2) apart: four per doubling."""
    if size <= 16:
        return 16
    low = power_of_two(size) // 2  # the power of two just below the size
    step = low // 4
    return -(-size // step) * step


rules = {
    "multiple of 16": multiple_of_16,
    "power of two": power_of_two,
    "four per doubling": quarter_classes,
}
asked = sum(REQUESTS)
print(f"{asked} bytes asked in {len(REQUESTS)} requests")
for name, rule in rules.items():
    wasted = sum(rule(size) - size for size in REQUESTS)
    classes = len({rule(size) for size in range(1, LIMIT + 1)})
    print(
        f"{name:<18} wasted {wasted:>5} bytes ({100 * wasted / asked:4.1f}%), "
        f"{classes:>3} block sizes up to {LIMIT}"
    )
