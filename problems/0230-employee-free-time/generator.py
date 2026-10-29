"""Seeded inputs for employee-free-time: n intervals over about n/10 employees.

The day is cut into blocks of 100 time units. An interval always lies in the first half of
one block, on a grid of 5 units, and each employee uses distinct blocks, so their own
intervals are sorted and separated. The second half of every block is nobody's working time,
so most gaps between used blocks are free, and holes inside a block are free when no
employee covers them. The grid makes intervals of different employees touch and nest often.
With n intervals there are about 2.75n distinct endpoints and n/4 or more free segments;
checking every elementary segment against every interval is quadratic at every seed, while
sorting (or merging the employees' sorted lists with a heap) costs n log n.
"""

import random
from itertools import pairwise

MAX_EMPLOYEES = 1000
MAX_PER_EMPLOYEE = 100
MAX_TOTAL = 10**4
MAX_TIME = 10**8
BLOCK = 100
GRID = 5
SLOTS = 10  # grid points 0..SLOTS cover the first half of a block


def generate(rng: random.Random, n: int) -> dict:
    total = min(max(n, 1), MAX_TOTAL)
    employees = min(MAX_EMPLOYEES, max(1, total // 10))
    counts = [1] * employees
    for _ in range(total - employees):
        person = rng.randrange(employees)
        while counts[person] == MAX_PER_EMPLOYEE:
            person = (person + 1) % employees
        counts[person] += 1
    blocks = max(total // 4, max(counts))
    schedule = []
    for count in counts:
        shifts = []
        for block in sorted(rng.sample(range(blocks), count)):
            first = rng.randint(0, SLOTS - 1)
            last = rng.randint(first + 1, SLOTS)
            shifts.append([block * BLOCK + GRID * first, block * BLOCK + GRID * last])
        schedule.append(shifts)
    rng.shuffle(schedule)
    return {"schedule": schedule}


def validate(case_input: dict) -> None:
    schedule = case_input["schedule"]
    assert 1 <= len(schedule) <= MAX_EMPLOYEES, "employee count out of range"
    assert sum(len(shifts) for shifts in schedule) <= MAX_TOTAL, "too many intervals"
    for shifts in schedule:
        assert 1 <= len(shifts) <= MAX_PER_EMPLOYEE, "interval count out of range"
        for interval in shifts:
            assert len(interval) == 2, "an interval has a start and an end"
            assert 0 <= interval[0] < interval[1] <= MAX_TIME, (
                "times out of range or not increasing"
            )
        for earlier, later in pairwise(shifts):
            assert earlier[1] < later[0], "an employee's intervals must be sorted and separated"
