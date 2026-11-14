"""Running Maximum (debugging): some tests fail. Find the bug and fix it."""


def running_max(nums: list[int]) -> list[int]:
    result: list[int] = []
    best = 0
    for value in nums:
        best = max(best, value)
        result.append(best)
    return result
