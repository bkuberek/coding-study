from itertools import islice
from math import prod


def product_except_self(nums: list[int]) -> list[int]:
    # math.prod over islice multiplies in C without copying: still n - 1 products per position.
    return [prod(islice(nums, i)) * prod(islice(nums, i + 1, None)) for i in range(len(nums))]
