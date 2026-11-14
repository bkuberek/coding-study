"""Seeded inputs for single-threaded-cpu: `n` tasks as [enqueue time, processing time].

Each input picks one of three regimes. In "backlog", every task arrives within a short window
and processing times are long, so a large queue builds up and the shortest-job rule decides
everything. In "sparse", arrivals are spread far apart and processing times are short, so the
CPU idles between tasks. In "ties", both times come from tiny ranges, so many tasks arrive
together with equal processing times and the index tie-break decides the order. Times reach
10^9, so the clock (a sum of processing times) can exceed the 32-bit range.

Below 100 tasks, which covers the oracle's inputs, the regime is drawn per input. From 100
tasks on, the sizes the ladder times, it is always "backlog": the heap then holds almost every
task at once, the worst case of the heap approach, at every seed, instead of a queue whose
size depends on the regime a seed draws.
"""

import random

MIN_TASKS = 1
MAX_TASKS = 10**5
TIME_LIMIT = 10**9
REGIMES = ("backlog", "sparse", "ties")
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_TASKS), MAX_TASKS)
    regime = rng.choice(REGIMES)
    if count >= UNIFORM_FROM:
        regime = "backlog"
    if regime == "backlog":
        arrival_limit, processing_limit = 10, TIME_LIMIT
    elif regime == "sparse":
        arrival_limit, processing_limit = TIME_LIMIT, 1000
    else:
        arrival_limit, processing_limit = 5, 3
    tasks = [
        [rng.randint(1, arrival_limit), rng.randint(1, processing_limit)] for _ in range(count)
    ]
    return {"tasks": tasks}


def validate(case_input: dict) -> None:
    tasks = case_input["tasks"]
    assert MIN_TASKS <= len(tasks) <= MAX_TASKS, "task count out of range"
    for task in tasks:
        assert len(task) == 2, "a task is [enqueue time, processing time]"
        assert all(1 <= value <= TIME_LIMIT for value in task), "time out of range"
