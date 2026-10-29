from bisect import bisect_left, bisect_right

MODULUS = 10**9 + 7


def create_sorted_array(instructions: list[int]) -> int:
    ordered: list[int] = []
    cost = 0
    for value in instructions:
        less = bisect_left(ordered, value)
        greater = len(ordered) - bisect_right(ordered, value)
        cost += min(less, greater)
        ordered.insert(len(ordered) - greater, value)
    return cost % MODULUS
