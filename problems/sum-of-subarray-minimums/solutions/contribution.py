MOD = 10**9 + 7


def sum_subarray_mins(arr: list[int]) -> int:
    total = 0
    # Indexes whose values strictly increase from bottom to top.
    stack: list[int] = []
    # One extra step with value 0, below every element, pops whatever is left.
    for index in range(len(arr) + 1):
        value = arr[index] if index < len(arr) else 0
        while stack and arr[stack[-1]] >= value:
            middle = stack.pop()
            # Starts after the previous strictly smaller element, ends before the next
            # smaller-or-equal one (index): arr[middle] is the minimum of left * right subarrays.
            left = middle - (stack[-1] if stack else -1)
            right = index - middle
            total += arr[middle] * left * right
        stack.append(index)
    return total % MOD
