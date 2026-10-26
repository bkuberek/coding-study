from itertools import pairwise


def contains_duplicate(nums: list[int]) -> bool:
    # sorted() returns a new list, so the caller's array keeps its order.
    return any(left == right for left, right in pairwise(sorted(nums)))
