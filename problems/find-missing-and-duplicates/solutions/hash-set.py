def find_missing_and_duplicates(nums: list[int]) -> list[list[int]]:
    seen: set[int] = set()
    repeated: set[int] = set()
    for value in nums:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    # Walking 1..n instead of the sets keeps both answers sorted without a sort.
    missing = [value for value in range(1, len(nums) + 1) if value not in seen]
    duplicated = [value for value in range(1, len(nums) + 1) if value in repeated]
    return [missing, duplicated]
