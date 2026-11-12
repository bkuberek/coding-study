"""Seeded inputs for check-task-order: a hidden task order with long prerequisite chains.

There are n tasks (capped at 5000), numbered 0 to n - 1 and placed in a random hidden order.
Each task requires the previous one in that order with probability 0.8, and extra pairs that
respect the hidden order bring the pair count to about 2n. The proposed order is the hidden
order, so it is valid.

Above 100 tasks every input stays valid, so that every approach reads all of the order and
all of the pairs at every ladder size: scanning for the places of both tasks of each pair then
reads about n / 2 entries per task, m * n in total, while the position table reads each entry
once. Up to 100 tasks the input is valid half of the time. The rest are broken in one of five
ways: the two tasks of one pair swap places, the last task is dropped, the last task is
replaced by a repeat of another one, the order is reversed, or a pair is reversed to close a
cycle with its twin. These cover the checks the approaches share.

Pairs are distinct, never join a task to itself, and are shuffled.
"""

import random

MIN_TASKS = 1
MAX_TASKS = 5000
MAX_PAIRS = 10**4
CHAIN_PROBABILITY = 0.8
LARGE = 100
BREAKS = 5


def generate(rng: random.Random, n: int) -> dict:
    tasks = min(max(n, MIN_TASKS), MAX_TASKS)
    hidden = list(range(tasks))
    rng.shuffle(hidden)
    pairs: set[tuple[int, int]] = set()
    for position in range(1, tasks):
        if rng.random() < CHAIN_PROBABILITY:
            pairs.add((hidden[position - 1], hidden[position]))
    budget = min(2 * tasks, MAX_PAIRS, tasks * (tasks - 1) // 2)
    for _ in range(4 * budget):
        if len(pairs) >= budget:
            break
        before, after = sorted(rng.sample(range(tasks), 2))
        pairs.add((hidden[before], hidden[after]))
    order = list(hidden)
    if tasks <= LARGE and rng.random() < 0.5:
        _break(rng, tasks, pairs, order)
    prerequisites = sorted(list(pair) for pair in pairs)
    rng.shuffle(prerequisites)
    return {"n": tasks, "prerequisites": prerequisites, "order": order}


def _break(rng: random.Random, tasks: int, pairs: set[tuple[int, int]], order: list[int]) -> None:
    kind = rng.randrange(BREAKS)
    if kind == 0 and pairs:
        before, after = rng.choice(sorted(pairs))
        first, second = order.index(before), order.index(after)
        order[first], order[second] = order[second], order[first]
    elif kind == 1:
        order.pop()
    elif kind == 2 and tasks >= 2:
        order[-1] = order[rng.randrange(tasks - 1)]
    elif kind == 3:
        order.reverse()
    elif pairs:
        before, after = rng.choice(sorted(pairs))
        pairs.add((after, before))


def validate(case_input: dict) -> None:
    tasks = case_input["n"]
    prerequisites, order = case_input["prerequisites"], case_input["order"]
    assert MIN_TASKS <= tasks <= MAX_TASKS, "task count out of range"
    assert len(prerequisites) <= MAX_PAIRS, "too many prerequisite pairs"
    assert all(len(pair) == 2 for pair in prerequisites), "prerequisites need two tasks"
    assert all(0 <= value < tasks for pair in prerequisites for value in pair), "task out of range"
    assert all(before != after for before, after in prerequisites), "a task cannot precede itself"
    assert len({tuple(pair) for pair in prerequisites}) == len(prerequisites), "pairs must be distinct"
    assert len(order) <= tasks, "the order is longer than the task count"
    assert all(0 <= task < tasks for task in order), "order entry out of range"
