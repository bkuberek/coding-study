"""Seeded inputs for parallel-courses: a hidden course order with long prerequisite chains.

There are n courses (capped at 3000), labelled 1 to n and listed in a random hidden order.
Each course requires the previous one in that order with probability 0.8, so the longest
chain, and with it the number of semesters, grows with n: a semester-by-semester scan of
every course then costs about V^2 checks, while the level-by-level topological sort and the
memoized search stay linear. Extra pairs that respect the hidden order bring the relation
count to about 2n.

Half of the inputs then get a cycle among a few courses late in the hidden order. Pairs are
distinct, never join a course to itself, and are shuffled.
"""

import random

MIN_COURSES = 1
MAX_COURSES = 3000
MAX_RELATIONS = 5000
CHAIN_PROBABILITY = 0.8
MAX_CYCLE = 6


def generate(rng: random.Random, n: int) -> dict:
    courses = min(max(n, MIN_COURSES), MAX_COURSES)
    order = list(range(1, courses + 1))
    rng.shuffle(order)
    pairs: set[tuple[int, int]] = set()
    for position in range(1, courses):
        if rng.random() < CHAIN_PROBABILITY:
            pairs.add((order[position - 1], order[position]))
    budget = min(2 * courses, MAX_RELATIONS - MAX_CYCLE, courses * (courses - 1) // 2)
    for _ in range(4 * budget):
        if len(pairs) >= budget:
            break
        before, after = sorted(rng.sample(range(courses), 2))
        pairs.add((order[before], order[after]))
    if courses >= 2 and rng.random() < 0.5:
        size = rng.randint(2, min(MAX_CYCLE, courses))
        low = courses // 2 if courses - courses // 2 >= size else 0
        cycle = [order[position] for position in sorted(rng.sample(range(low, courses), size))]
        for before, after in zip(cycle, cycle[1:]):
            pairs.add((before, after))
        pairs.add((cycle[-1], cycle[0]))
    relations = sorted(list(pair) for pair in pairs)
    rng.shuffle(relations)
    return {"n": courses, "relations": relations}


def validate(case_input: dict) -> None:
    courses, relations = case_input["n"], case_input["relations"]
    assert MIN_COURSES <= courses <= MAX_COURSES, "course count out of range"
    assert len(relations) <= MAX_RELATIONS, "too many relations"
    assert all(len(pair) == 2 for pair in relations), "relations need two courses"
    assert all(1 <= value <= courses for pair in relations for value in pair), "course out of range"
    assert all(before != after for before, after in relations), "a course cannot precede itself"
    assert len({tuple(pair) for pair in relations}) == len(relations), "relations must be distinct"
