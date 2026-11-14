def missing_number(nums: list[int]) -> int:
    # In the sorted array, value i sits at index i until the gap.
    for index, value in enumerate(sorted(nums)):
        if value != index:
            return index
    return len(nums)
