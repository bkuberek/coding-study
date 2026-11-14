def majority_element(nums: list[int]) -> int:
    half = len(nums) // 2
    counts: dict[int, int] = {}
    for value in nums:
        counts[value] = counts.get(value, 0) + 1
        if counts[value] > half:
            return value
    raise ValueError("no majority element")
