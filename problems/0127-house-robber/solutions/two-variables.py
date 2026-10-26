def rob(nums: list[int]) -> int:
    # Before each house: without_last and with_last are the best totals for the prefixes
    # that end two houses back and one house back.
    without_last, with_last = 0, 0
    for cash in nums:
        without_last, with_last = with_last, max(with_last, without_last + cash)
    return with_last
