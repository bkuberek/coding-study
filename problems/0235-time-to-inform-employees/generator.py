"""Seeded inputs for time-to-inform-employees: a long management chain with a bushy rest.

Employees are listed in a random hidden order whose first entry is the head. The first half
of that order (at most 2000 people) forms one chain, each reporting to the previous one;
everyone after it reports to a uniformly chosen earlier employee, or to the head when that
would put more than 2000 managers above them. Walking up from every employee to the head
then costs about n^2 / 4 steps at every seed up to n = 4000, while a top-down traversal
visits each employee once. Managers need 1 to 1000 minutes to pass the news on, except that
at oracle sizes (30 or fewer) a fifth of them need 0; employees without reports need 0.
"""

import random

MAX_EMPLOYEES = 10**5
MAX_DEPTH = 2000
MAX_MINUTES = 1000
SMALL_UP_TO = 30
INSTANT_SHARE = 0.2


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_EMPLOYEES)
    order = list(range(count))
    rng.shuffle(order)
    chain = min(MAX_DEPTH, max(1, count // 2))
    manager = [-1] * count
    depth = [0] * count
    for position in range(1, count):
        employee = order[position]
        boss = order[position - 1] if position < chain else order[rng.randrange(position)]
        if depth[boss] + 1 > MAX_DEPTH:
            boss = order[0]
        manager[employee] = boss
        depth[employee] = depth[boss] + 1
    has_reports = [False] * count
    for boss in manager:
        if boss != -1:
            has_reports[boss] = True
    small = count <= SMALL_UP_TO
    inform_time = [
        0
        if not has_reports[employee] or (small and rng.random() < INSTANT_SHARE)
        else rng.randint(1, MAX_MINUTES)
        for employee in range(count)
    ]
    return {"n": count, "headID": order[0], "manager": manager, "informTime": inform_time}


def validate(case_input: dict) -> None:
    count, head = case_input["n"], case_input["headID"]
    manager, inform_time = case_input["manager"], case_input["informTime"]
    assert 1 <= count <= MAX_EMPLOYEES, "employee count out of range"
    assert len(manager) == count, "manager must have n entries"
    assert len(inform_time) == count, "informTime must have n entries"
    assert 0 <= head < count, "head out of range"
    assert manager[head] == -1, "the head reports to nobody"
    assert all(boss == -1 or 0 <= boss < count for boss in manager), "manager out of range"
    assert sum(1 for boss in manager if boss == -1) == 1, "only the head reports to nobody"
    has_reports = {boss for boss in manager if boss != -1}
    for employee, minutes in enumerate(inform_time):
        assert 0 <= minutes <= MAX_MINUTES, "minutes out of range"
        assert employee in has_reports or minutes == 0, "employees without reports need 0 minutes"
    for employee in range(count):
        steps, current = 0, employee
        while current != head:
            current = manager[current]
            steps += 1
            assert steps <= MAX_DEPTH, "the chain is too long or has a cycle"
