from bisect import bisect_left


def length_of_lis(nums: list[int]) -> int:
    # tails[L - 1] is the smallest last value of any increasing subsequence of length L seen
    # so far; it is strictly increasing, so it can be binary searched.
    tails: list[int] = []
    for value in nums:
        position = bisect_left(tails, value)
        if position == len(tails):
            tails.append(value)
        else:
            tails[position] = value
    return len(tails)
