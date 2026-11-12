"""Breadth-first search on a tram map: fewest stops from harbor to every station, and a route."""

from collections import deque

lines = {
    "harbor": ["market", "museum"],
    "market": ["harbor", "park"],
    "museum": ["harbor", "park", "school"],
    "park": ["market", "museum", "stadium"],
    "school": ["museum", "library", "stadium"],
    "stadium": ["park", "school", "zoo"],
    "library": ["school"],
    "zoo": ["stadium"],
}


def bfs(start: str) -> tuple[dict[str, int], dict[str, str | None]]:
    stops = {start: 0}  # doubles as the visited set
    came_from: dict[str, str | None] = {start: None}
    queue = deque([start])
    while queue:
        station = queue.popleft()
        for nearby in lines[station]:
            if nearby not in stops:  # mark it now, when it is discovered
                stops[nearby] = stops[station] + 1
                came_from[nearby] = station
                queue.append(nearby)
        print(f"take {station:<8} queue: {list(queue)}")
    return stops, came_from


stops, came_from = bfs("harbor")

levels: dict[int, list[str]] = {}
for station, count in stops.items():
    levels.setdefault(count, []).append(station)
for count, stations in levels.items():
    print(f"level {count}: {stations}")

route = []
station: str | None = "zoo"
while station is not None:
    route.append(station)
    station = came_from[station]
print("route:", " -> ".join(reversed(route)), f"({stops['zoo']} stops)")
