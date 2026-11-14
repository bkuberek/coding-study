def find_kth_largest(nums: list[int], k: int) -> int:
    return sorted(nums)[len(nums) - k]
