def permute(nums: list[int]) -> list[list[int]]:
    values = nums.copy()
    result: list[list[int]] = []

    def fix_slot(slot: int) -> None:
        # values[:slot] is the fixed prefix; values[slot:] are the candidates still free.
        if slot == len(values):
            result.append(values.copy())
            return
        for candidate in range(slot, len(values)):
            values[slot], values[candidate] = values[candidate], values[slot]
            fix_slot(slot + 1)
            values[slot], values[candidate] = values[candidate], values[slot]

    fix_slot(0)
    return result
