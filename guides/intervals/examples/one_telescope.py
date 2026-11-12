"""One telescope, many observation requests [start, end) in hours. Grant as many as possible with no
two overlapping. Three greedy rules take requests in a different order; only one is always best."""

from collections.abc import Callable
from itertools import combinations

Interval = tuple[int, int]
Rule = Callable[[Interval], int]

RULES: dict[str, Rule] = {
    "earliest start": lambda request: request[0],
    "shortest first": lambda request: request[1] - request[0],
    "earliest end": lambda request: request[1],
}


def overlap(first: Interval, second: Interval) -> bool:
    return first[0] < second[1] and second[0] < first[1]


def greedy(requests: list[Interval], rule: Rule) -> list[Interval]:
    granted: list[Interval] = []
    for request in sorted(requests, key=rule):
        if not any(overlap(request, kept) for kept in granted):
            granted.append(request)
    return granted


def most_by_brute_force(requests: list[Interval]) -> int:
    return max(
        size
        for size in range(len(requests) + 1)
        for chosen in combinations(requests, size)
        if not any(overlap(a, b) for a, b in combinations(chosen, 2))
    )


for requests in ([(0, 10), (1, 3), (4, 6), (7, 9)], [(0, 5), (4, 7), (6, 11)]):
    print(f"requests {requests}: best is {most_by_brute_force(requests)}")
    for name, rule in RULES.items():
        print(f"  {name:<14} grants {greedy(requests, rule)}")

every_request = [(start, end) for start in range(6) for end in range(start + 1, 6)]
inputs = [list(chosen) for size in (1, 2, 3, 4) for chosen in combinations(every_request, size)]
print(f"every set of 1 to 4 requests within hours 0 to 5: {len(inputs)} inputs")
for name, rule in RULES.items():
    wrong = sum(len(greedy(requests, rule)) < most_by_brute_force(requests) for requests in inputs)
    print(f"  {name:<14} falls short on {wrong}")
