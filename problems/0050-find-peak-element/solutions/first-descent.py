def find_peak_element(nums: list[int]) -> int:
    # Before the first descent the values only rise, so the element just before it beats both
    # neighbors. With no descent at all, the last element is the peak.
    for index in range(len(nums) - 1):
        if nums[index] > nums[index + 1]:
            return index
    return len(nums) - 1
