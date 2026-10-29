"""Seeded inputs for employee-importance.

n employees with distinct ids from 1 to 10^5 and importance from -100 to 100. Each employee
after the first reports to a uniformly chosen earlier one (a random recursive tree, whose
depth stays near e * ln n), and the records are shuffled. From 31 employees on, which covers
every ladder size, the query is the top of the hierarchy, so every record is visited and
finding each one by scanning costs about n^2 / 2 steps at every seed, against n for a map.
At oracle sizes (30 employees or fewer) a fifth of the employees report to nobody, making a
forest, and the query is a random employee.
"""

import random

MAX_EMPLOYEES = 10**4
MAX_ID = 10**5
MAX_IMPORTANCE = 100
MAX_DEPTH = 1000
SMALL_UP_TO = 30
TOP_SHARE = 0.2


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_EMPLOYEES)
    ids = rng.sample(range(1, MAX_ID + 1), count)
    small = count <= SMALL_UP_TO
    subordinates: dict[int, list[int]] = {employee: [] for employee in ids}
    for position in range(1, count):
        if small and rng.random() < TOP_SHARE:
            continue
        subordinates[ids[rng.randrange(position)]].append(ids[position])
    employees = []
    for employee in ids:
        reports = subordinates[employee]
        rng.shuffle(reports)
        employees.append([employee, rng.randint(-MAX_IMPORTANCE, MAX_IMPORTANCE), *reports])
    rng.shuffle(employees)
    query = rng.choice(ids) if small else ids[0]
    return {"employees": employees, "employeeId": query}


def validate(case_input: dict) -> None:
    employees, query = case_input["employees"], case_input["employeeId"]
    assert 1 <= len(employees) <= MAX_EMPLOYEES, "employee count out of range"
    assert all(len(record) >= 2 for record in employees), "a record holds an id and an importance"
    ids = [record[0] for record in employees]
    known = set(ids)
    assert len(known) == len(ids), "ids must be distinct"
    assert all(1 <= employee <= MAX_ID for employee in ids), "id out of range"
    assert all(-MAX_IMPORTANCE <= record[1] <= MAX_IMPORTANCE for record in employees), (
        "importance out of range"
    )
    assert query in known, "the queried employee must exist"
    leader: dict[int, int] = {}
    for record in employees:
        for report in record[2:]:
            assert report in known, "a subordinate must exist"
            assert report not in leader, "an employee has at most one direct leader"
            leader[report] = record[0]
    for employee in ids:
        depth, current = 0, employee
        while current in leader:
            current = leader[current]
            depth += 1
            assert depth <= MAX_DEPTH, "the hierarchy is too deep or has a cycle"
