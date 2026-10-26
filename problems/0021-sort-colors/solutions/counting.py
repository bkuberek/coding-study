def sort_colors(nums: list[int]) -> None:
    counts = [0, 0, 0]
    for color in nums:
        counts[color] += 1
    index = 0
    for color, count in enumerate(counts):
        for _ in range(count):
            nums[index] = color
            index += 1
