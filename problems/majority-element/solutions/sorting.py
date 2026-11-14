def majority_element(nums: list[int]) -> int:
    # The majority block covers more than half of the sorted positions, so it covers the middle.
    return sorted(nums)[len(nums) // 2]
