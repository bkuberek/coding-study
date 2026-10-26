def longest_ones(nums: list[int], k: int) -> int:
    best = 0
    for start in range(len(nums)):
        zeros = 0
        end = start
        while end < len(nums):
            if nums[end] == 0:
                if zeros == k:
                    break
                zeros += 1
            end += 1
        best = max(best, end - start)
    return best
