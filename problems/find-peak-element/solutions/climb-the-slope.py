def find_peak_element(nums: list[int]) -> int:
    # Invariant: some peak of the whole array lies in [low, high].
    low, high = 0, len(nums) - 1
    while low < high:
        middle = (low + high) // 2
        if nums[middle] < nums[middle + 1]:
            low = middle + 1
        else:
            high = middle
    return low
