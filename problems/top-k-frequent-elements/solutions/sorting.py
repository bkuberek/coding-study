from collections import Counter


def top_k_frequent(nums: list[int], k: int) -> list[int]:
    counts = Counter(nums)
    by_count = sorted(counts, key=counts.__getitem__, reverse=True)
    return by_count[:k]
