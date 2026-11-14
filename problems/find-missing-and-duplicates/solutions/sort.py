def find_missing_and_duplicates(nums: list[int]) -> list[list[int]]:
    nums.sort()
    missing: list[int] = []
    duplicated: list[int] = []
    expected = 1  # the smallest value not accounted for yet
    previous = 0
    for value in nums:
        if value == previous:
            # A third copy must not list the value again.
            if not duplicated or duplicated[-1] != value:
                duplicated.append(value)
            continue
        missing.extend(range(expected, value))
        expected = value + 1
        previous = value
    missing.extend(range(expected, len(nums) + 1))
    return [missing, duplicated]
