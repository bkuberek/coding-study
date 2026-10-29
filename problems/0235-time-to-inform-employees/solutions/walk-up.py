def num_of_minutes(n: int, head_id: int, manager: list[int], inform_time: list[int]) -> int:
    longest = 0
    for employee in range(n):
        # The news reaches employee after every manager above them has passed it on.
        elapsed = 0
        current = employee
        while current != head_id:
            current = manager[current]
            elapsed += inform_time[current]
        longest = max(longest, elapsed)
    return longest
