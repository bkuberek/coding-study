"""Seeded inputs for course-schedule: a hidden course order with long prerequisite chains.

There are n courses (capped at 2000), listed in a random hidden order. Each course requires
the previous one in that order with probability 0.8, which makes chains long: in a long
chain only one course is free at a time, so repeatedly scanning for a free course costs
about V^2 / 2 checks, while the queue-based and depth-first approaches stay linear. Random
extra prerequisites that respect the hidden order bring the pair count to about 2n.

Half of the inputs then get a cycle: a few courses late in the hidden order, joined by
forward pairs and closed by one pair pointing back. Pairs are distinct and never join a
course to itself, and they are shuffled.
"""

import random

MIN_COURSES = 1
MAX_COURSES = 2000
MAX_PAIRS = 5000
CHAIN_PROBABILITY = 0.8
MAX_CYCLE = 6


def generate(rng: random.Random, n: int) -> dict:
    courses = min(max(n, MIN_COURSES), MAX_COURSES)
    order = list(range(courses))
    rng.shuffle(order)
    pairs: set[tuple[int, int]] = set()
    for position in range(1, courses):
        if rng.random() < CHAIN_PROBABILITY:
            pairs.add((order[position], order[position - 1]))
    budget = min(2 * courses, MAX_PAIRS - MAX_CYCLE, courses * (courses - 1) // 2)
    for _ in range(4 * budget):
        if len(pairs) >= budget:
            break
        before, after = sorted(rng.sample(range(courses), 2))
        pairs.add((order[after], order[before]))
    if courses >= 2 and rng.random() < 0.5:
        size = rng.randint(2, min(MAX_CYCLE, courses))
        low = courses // 2 if courses - courses // 2 >= size else 0
        cycle = [order[position] for position in sorted(rng.sample(range(low, courses), size))]
        for before, after in zip(cycle, cycle[1:]):
            pairs.add((after, before))
        pairs.add((cycle[0], cycle[-1]))
    prerequisites = [list(pair) for pair in pairs]
    prerequisites.sort()
    rng.shuffle(prerequisites)
    return {"numCourses": courses, "prerequisites": prerequisites}


def validate(case_input: dict) -> None:
    courses, prerequisites = case_input["numCourses"], case_input["prerequisites"]
    assert MIN_COURSES <= courses <= MAX_COURSES, "course count out of range"
    assert len(prerequisites) <= MAX_PAIRS, "too many pairs"
    assert all(len(pair) == 2 for pair in prerequisites), "pairs need two courses"
    assert all(0 <= value < courses for pair in prerequisites for value in pair), "course out of range"
    assert all(course != required for course, required in prerequisites), "a course cannot require itself"
    assert len({tuple(pair) for pair in prerequisites}) == len(prerequisites), "pairs must be distinct"
