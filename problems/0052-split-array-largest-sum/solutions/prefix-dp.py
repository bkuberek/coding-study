def split_array(nums: list[int], k: int) -> int:
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    n = len(nums)
    # best[i]: the smallest cost of cutting nums[:i] into the current number of pieces.
    best = prefix[:]
    for pieces in range(2, k + 1):
        best = [0] * pieces + [
            min(max(best[cut], prefix[end] - prefix[cut]) for cut in range(pieces - 1, end))
            for end in range(pieces, n + 1)
        ]
    return best[n]
