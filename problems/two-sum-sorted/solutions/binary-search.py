from bisect import bisect_left


def two_sum_sorted(numbers: list[int], target: int) -> list[int]:
    for i, value in enumerate(numbers):
        complement = target - value
        j = bisect_left(numbers, complement, i + 1)
        if j < len(numbers) and numbers[j] == complement:
            return [i, j]
    return []
