def last_stone_weight(stones: list[int]) -> int:
    remaining = list(stones)
    while len(remaining) > 1:
        remaining.sort()
        heaviest = remaining.pop()
        second = remaining.pop()
        if heaviest != second:
            remaining.append(heaviest - second)
    return remaining[0] if remaining else 0
