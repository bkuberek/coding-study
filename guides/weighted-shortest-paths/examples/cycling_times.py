"""Fewest roads is not fastest: BFS against Dijkstra's algorithm on cycling times in minutes."""

import heapq
from collections import deque
from itertools import pairwise

roads = [
    ("home", "bridge", 12),
    ("home", "bakery", 3),
    ("bakery", "park", 4),
    ("park", "bridge", 2),
    ("park", "river", 5),
    ("bridge", "office", 6),
    ("river", "office", 5),
]
near: dict[str, list[tuple[str, int]]] = {}
time_of: dict[tuple[str, str], int] = {}
for a, b, minutes in roads:
    near.setdefault(a, []).append((b, minutes))
    near.setdefault(b, []).append((a, minutes))
    time_of[a, b] = time_of[b, a] = minutes


def route(came_from: dict[str, str | None], place: str) -> list[str]:
    steps = []
    current: str | None = place
    while current is not None:
        steps.append(current)
        current = came_from[current]
    return steps[::-1]


def fewest_roads(start: str, goal: str) -> list[str]:
    came_from: dict[str, str | None] = {start: None}
    queue = deque([start])
    while queue:
        place = queue.popleft()
        for nxt, _ in near[place]:
            if nxt not in came_from:
                came_from[nxt] = place
                queue.append(nxt)
    return route(came_from, goal)


def dijkstra(start: str, goal: str) -> tuple[int, list[str]]:
    best = {start: 0}
    came_from: dict[str, str | None] = {start: None}
    settled: set[str] = set()
    heap = [(0, start)]
    while heap:
        minutes, place = heapq.heappop(heap)
        if place in settled:
            print(f"  skip  {place:<7} at {minutes:>2}: an outdated entry")
            continue
        settled.add(place)  # no route found later can be shorter than this one
        print(f"  settle {place:<6} at {minutes:>2}")
        if place == goal:
            return minutes, route(came_from, goal)
        for nxt, cost in near[place]:
            if nxt not in settled and minutes + cost < best.get(nxt, float("inf")):
                best[nxt] = minutes + cost
                came_from[nxt] = place
                heapq.heappush(heap, (minutes + cost, nxt))
    raise ValueError(f"{goal} cannot be reached")


hops = fewest_roads("home", "office")
total = sum(time_of[step] for step in pairwise(hops))
print("fewest roads:", " -> ".join(hops), "=", total, "minutes")
minutes, fastest = dijkstra("home", "office")
print("fastest:", " -> ".join(fastest), "=", minutes, "minutes")
