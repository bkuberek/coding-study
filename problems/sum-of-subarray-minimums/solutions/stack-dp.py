MOD = 10**9 + 7


def sum_subarray_mins(arr: list[int]) -> int:
    # ending[i] is the sum of the minimums of the subarrays that end at i.
    ending = [0] * len(arr)
    # Indexes whose values strictly increase from bottom to top.
    stack: list[int] = []
    for index, value in enumerate(arr):
        while stack and arr[stack[-1]] >= value:
            stack.pop()
        if stack:
            previous = stack[-1]
            # Starts after the previous smaller element have minimum `value`; earlier starts
            # have the same minimums as the subarrays ending at `previous`.
            ending[index] = ending[previous] + value * (index - previous)
        else:
            ending[index] = value * (index + 1)
        stack.append(index)
    return sum(ending) % MOD
