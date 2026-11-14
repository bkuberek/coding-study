"""How many levels, and so how many page reads, a lookup needs, for different fan-outs.

A perfectly balanced binary search tree of height h holds up to 2**h - 1 keys. A tree whose nodes
each have f children reaches f**h leaves' worth of entries in h levels. The model: 8,192-byte
pages and 16-byte entries (a key and a pointer), so a full page holds 512 entries and a half-full
one 256. Only whole numbers are used, so nothing depends on floating-point rounding.
"""

PAGE_BYTES, ENTRY_BYTES = 8192, 16
FULL = PAGE_BYTES // ENTRY_BYTES


def binary_height(n: int) -> int:
    h = 0
    while 2**h - 1 < n:
        h += 1
    return h


def levels(n: int, fanout: int) -> int:
    h = 1
    while fanout**h < n:
        h += 1
    return h


print(f"a full page holds {FULL} entries")
print(f"{'keys':>15} {'binary tree':>12} {'fan-out 100':>12} {'half full':>10} {'full':>6}")
for n in [1_000, 1_000_000, 1_000_000_000, 1_000_000_000_000]:
    print(
        f"{n:>15,} {binary_height(n):>12} {levels(n, 100):>12}"
        f" {levels(n, FULL // 2):>10} {levels(n, FULL):>6}"
    )
