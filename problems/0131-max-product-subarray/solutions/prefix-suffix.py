def max_product(nums: list[int]) -> int:
    # Within a zero-free run, the best product is a prefix or a suffix of the run, so the
    # running products from both ends (restarted after each zero) cover every candidate.
    best = max(nums)
    from_left = from_right = 1
    n = len(nums)
    for i in range(n):
        from_left = (from_left or 1) * nums[i]
        from_right = (from_right or 1) * nums[n - 1 - i]
        best = max(best, from_left, from_right)
    return best
