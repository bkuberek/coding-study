from functools import reduce
from operator import xor


def single_number(nums: list[int]) -> int:
    # Pairs cancel (a ^ a == 0) in any order; Python's XOR on negative ints acts on
    # two's complement with unlimited sign bits, so the result keeps its sign.
    return reduce(xor, nums, 0)
