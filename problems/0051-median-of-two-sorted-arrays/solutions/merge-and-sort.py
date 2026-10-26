def find_median_sorted_arrays(nums1: list[int], nums2: list[int]) -> float:
    merged = sorted(nums1 + nums2)
    middle = len(merged) // 2
    if len(merged) % 2 == 1:
        return float(merged[middle])
    return (merged[middle - 1] + merged[middle]) / 2
