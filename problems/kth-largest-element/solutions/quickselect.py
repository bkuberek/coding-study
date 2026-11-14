import random


def find_kth_largest(nums: list[int], k: int) -> int:
    values = list(nums)
    target = len(values) - k  # the answer's index in ascending order
    low, high = 0, len(values) - 1
    while True:
        pivot = values[random.randint(low, high)]
        # Three-way partition of values[low..high]: < pivot | == pivot | > pivot.
        less, scan, greater = low, low, high
        while scan <= greater:
            if values[scan] < pivot:
                values[less], values[scan] = values[scan], values[less]
                less += 1
                scan += 1
            elif values[scan] > pivot:
                values[scan], values[greater] = values[greater], values[scan]
                greater -= 1
            else:
                scan += 1
        if target < less:
            high = less - 1
        elif target > greater:
            low = greater + 1
        else:
            return pivot
