def first_missing_positive(nums: list[int]) -> int:
    n = len(nums)
    for i in range(n):
        # Swap nums[i] to its home index nums[i] - 1 until the value here has no home in
        # range or its home already holds it. Every swap settles one value for good.
        while 1 <= nums[i] <= n and nums[nums[i] - 1] != nums[i]:
            home = nums[i] - 1
            nums[i], nums[home] = nums[home], nums[i]
    for i in range(n):
        if nums[i] != i + 1:
            return i + 1
    return n + 1
