def majority_element(nums: list[int]) -> int:
    half = len(nums) // 2
    for candidate in nums:
        # list.count scans the whole list in C: still n comparisons per candidate.
        if nums.count(candidate) > half:
            return candidate
    raise ValueError("no majority element")
