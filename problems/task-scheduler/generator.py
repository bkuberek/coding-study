"""Seeded inputs for task-scheduler: `n` task labels and a cooldown.

The number of task types is uniform between 1 and 26, and the labels are drawn with random
weights, so some inputs are dominated by one task (long idle stretches) and others spread
evenly (no idle time at all). The cooldown is small (0 to 3) half the time and up to 100
otherwise. The task order is random; the answer does not depend on it.
"""

import random
import string

MIN_TASKS = 1
MAX_TASKS = 10**4
MAX_COOLDOWN = 100
SMALL_COOLDOWN = 3


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_TASKS), MAX_TASKS)
    labels = rng.sample(string.ascii_uppercase, rng.randint(1, 26))
    weights = [rng.random() ** 3 + 0.01 for _ in labels]
    tasks = rng.choices(labels, weights=weights, k=count)
    limit = SMALL_COOLDOWN if rng.random() < 0.5 else MAX_COOLDOWN
    return {"tasks": tasks, "cooldown": rng.randint(0, limit)}


def validate(case_input: dict) -> None:
    tasks, cooldown = case_input["tasks"], case_input["cooldown"]
    assert MIN_TASKS <= len(tasks) <= MAX_TASKS, "task count out of range"
    assert all(task in string.ascii_uppercase for task in tasks), "tasks are uppercase letters"
    assert 0 <= cooldown <= MAX_COOLDOWN, "cooldown out of range"
