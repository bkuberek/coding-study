def count_smaller(nums: list[int]) -> list[int]:
    counts = [0] * len(nums)
    order = list(range(len(nums)))  # positions, sorted by value within each merged run
    buffer = [0] * len(nums)
    width = 1
    # Bottom-up merge sort of positions by value; no recursion needed.
    while width < len(nums):
        for low in range(0, len(nums), 2 * width):
            middle = min(low + width, len(nums))
            high = min(low + 2 * width, len(nums))
            left, right, out = low, middle, low
            while left < middle:
                if right < high and nums[order[right]] < nums[order[left]]:
                    buffer[out] = order[right]
                    right += 1
                else:
                    # Every right-half element taken so far is smaller and came after it.
                    counts[order[left]] += right - middle
                    buffer[out] = order[left]
                    left += 1
                out += 1
            buffer[out:high] = order[right:high]
        order, buffer = buffer, order
        width *= 2
    return counts
