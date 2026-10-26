from itertools import accumulate

MOD = 10**9 + 7


def sum_subarray_mins(arr: list[int]) -> int:
    total = 0
    for start in range(len(arr)):
        # accumulate(..., min) yields the minimum of arr[start:end] for every end, in order.
        total += sum(accumulate(arr[start:], min))
    return total % MOD
