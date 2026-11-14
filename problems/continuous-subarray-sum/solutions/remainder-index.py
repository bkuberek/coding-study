def check_subarray_sum(nums: list[int], k: int) -> bool:
    # first_index[r] is the earliest position whose prefix (ending there) leaves remainder r;
    # the empty prefix ends at position -1.
    first_index = {0: -1}
    remainder = 0
    for position, value in enumerate(nums):
        remainder = (remainder + value) % k
        earlier = first_index.setdefault(remainder, position)
        if position - earlier >= 2:
            return True
    return False
