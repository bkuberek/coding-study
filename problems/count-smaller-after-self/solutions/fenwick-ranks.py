def count_smaller(nums: list[int]) -> list[int]:
    # Coordinate compression: rank 1 is the smallest distinct value.
    rank = {value: position for position, value in enumerate(sorted(set(nums)), start=1)}
    size = len(rank)
    tree = [0] * (size + 1)  # Fenwick tree: how many seen values have each rank
    counts = [0] * len(nums)
    for i in range(len(nums) - 1, -1, -1):
        r = rank[nums[i]]
        # Seen values with a rank below r, i.e. strictly smaller values to the right.
        smaller, j = 0, r - 1
        while j > 0:
            smaller += tree[j]
            j -= j & -j
        counts[i] = smaller
        while r <= size:
            tree[r] += 1
            r += r & -r
    return counts
