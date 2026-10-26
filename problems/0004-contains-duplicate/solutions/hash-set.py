def contains_duplicate(nums: list[int]) -> bool:
    seen: set[int] = set()
    for value in nums:
        if value in seen:
            return True
        seen.add(value)
    return False
