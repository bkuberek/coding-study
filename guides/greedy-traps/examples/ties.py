"""Ties in a sort key and in a heap. Python's sort is stable, so equal keys keep their input order:
an incomplete key makes the result depend on how the input happened to be listed."""

import heapq
from collections.abc import Callable
from itertools import count
from typing import Any

Interval = tuple[int, int]


def earliest_end(requests: list[Interval], key: Callable[[Interval], Any]) -> list[Interval]:
    granted: list[Interval] = []
    for start, end in sorted(requests, key=key):
        if all(end <= kept_start or kept_end <= start for kept_start, kept_end in granted):
            granted.append((start, end))
    return granted


def end_only(request: Interval) -> int:
    return request[1]


def end_then_start(request: Interval) -> tuple[int, int]:
    return request[1], request[0]


def pop_order(entries: list[tuple[Any, ...]]) -> list[str]:
    heap: list[tuple[Any, ...]] = []
    for entry in entries:
        heapq.heappush(heap, entry)
    return [heapq.heappop(heap)[-1]["name"] for _ in entries]


listed = [(2, 5), (3, 5), (0, 2)]
relisted = [(0, 2), (3, 5), (2, 5)]
for key in (end_only, end_then_start):
    print(f"key {key.__name__}:")
    for requests in (listed, relisted):
        print(f"  {requests} -> grants {earliest_end(requests, key)}")

jobs = [(2, {"name": "scan"}), (1, {"name": "print"}), (2, {"name": "bind"})]
try:
    print("heap of (hours, job):", pop_order(jobs))
except TypeError as error:
    print("heap of (hours, job): TypeError:", error)
arrivals = count()
with_arrivals = [(hours, next(arrivals), job) for hours, job in jobs]
print("heap of (hours, arrival, job):", pop_order(with_arrivals))
