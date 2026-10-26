def two_sum(nums: list[int], target: int) -> list[int]:
    index_by_value: dict[int, int] = {}
    for i, value in enumerate(nums):
        partner = index_by_value.get(target - value)
        if partner is not None:
            return [partner, i]
        index_by_value[value] = i
    return []
