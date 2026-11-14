import bisect


def last_stone_weight(stones: list[int]) -> int:
    remaining = sorted(stones)
    while len(remaining) > 1:
        heaviest = remaining.pop()
        second = remaining.pop()
        if heaviest != second:
            # Binary search finds the slot in O(log n); shifting the tail to open it is O(n).
            bisect.insort(remaining, heaviest - second)
    return remaining[0] if remaining else 0
