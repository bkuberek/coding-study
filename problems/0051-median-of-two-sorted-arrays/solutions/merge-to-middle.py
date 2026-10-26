def find_median_sorted_arrays(nums1: list[int], nums2: list[int]) -> float:
    total = len(nums1) + len(nums2)
    i = j = 0
    previous = current = 0
    # Advance through the merged order until `current` is the value at position total // 2.
    for _ in range(total // 2 + 1):
        previous = current
        if j == len(nums2) or (i < len(nums1) and nums1[i] <= nums2[j]):
            current = nums1[i]
            i += 1
        else:
            current = nums2[j]
            j += 1
    if total % 2 == 1:
        return float(current)
    return (previous + current) / 2
