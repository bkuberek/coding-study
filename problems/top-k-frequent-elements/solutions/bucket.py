from collections import Counter


def top_k_frequent(nums: list[int], k: int) -> list[int]:
    counts = Counter(nums)
    # buckets[c] holds the values that occur exactly c times; no count exceeds len(nums).
    buckets: list[list[int]] = [[] for _ in range(len(nums) + 1)]
    for value, count in counts.items():
        buckets[count].append(value)
    answer: list[int] = []
    for count in range(len(nums), 0, -1):
        for value in buckets[count]:
            answer.append(value)
            if len(answer) == k:
                return answer
    return answer
