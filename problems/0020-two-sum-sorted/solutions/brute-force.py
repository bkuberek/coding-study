def two_sum_sorted(numbers: list[int], target: int) -> list[int]:
    for i, value in enumerate(numbers):
        try:
            # list.index scans numbers[i + 1:] in C: still one check per later element.
            return [i, numbers.index(target - value, i + 1)]
        except ValueError:
            continue
    return []
