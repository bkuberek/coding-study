"""Why a task should replace its partition, and read the day it is run for, not the clock.

A daily task adds up one day of orders and writes the total into that day's partition. Its first
attempt writes and then loses its success signal, so the scheduler runs it again.
"""

ORDERS = {1: [5, 7], 2: [4], 3: [10, 2, 3]}  # day -> order amounts, one partition per day


class PartitionedTable:
    def __init__(self) -> None:
        self.partitions: dict[int, list[int]] = {}

    def append(self, day: int, rows: list[int]) -> None:
        self.partitions.setdefault(day, []).extend(rows)

    def overwrite(self, day: int, rows: list[int]) -> None:
        self.partitions[day] = list(rows)


for mode in ("append", "overwrite"):
    table = PartitionedTable()
    write = getattr(table, mode)
    for _attempt in (1, 2):  # attempt 1 wrote, then its success signal was lost
        write(3, [sum(ORDERS[3])])
    print(f"{mode:>9}: day 3 holds {table.partitions[3]}, a report reads {sum(table.partitions[3])}")


def total_for_yesterday(run_on_day: int) -> int:
    return sum(ORDERS.get(run_on_day - 1, []))


def total_for(day: int) -> int:
    return sum(ORDERS.get(day, []))


print("day 2, run on day 3:", total_for_yesterday(3), "and", total_for(2))
print("day 2, rerun on day 9:", total_for_yesterday(9), "and", total_for(2))
