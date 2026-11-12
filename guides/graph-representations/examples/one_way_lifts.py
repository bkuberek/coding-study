"""A directed graph: ski lifts only go up, so each edge is stored once, from where it starts."""

stations = ["base", "lake", "ridge", "summit", "chapel"]
lifts = [("base", "ridge"), ("lake", "ridge"), ("ridge", "summit")]

out_edges: dict[str, list[str]] = {station: [] for station in stations}
in_degree = dict.fromkeys(stations, 0)
for start, end in lifts:
    out_edges[start].append(end)  # one direction only
    in_degree[end] += 1

for station in stations:
    print(
        f"{station:>6}: lifts to {out_edges[station]}, "
        f"out-degree {len(out_edges[station])}, in-degree {in_degree[station]}"
    )

# The reverse graph answers "which lifts arrive here?" as fast as out_edges answers "where to?".
in_edges: dict[str, list[str]] = {station: [] for station in stations}
for start, end in lifts:
    in_edges[end].append(start)
print("lifts arriving at ridge come from", in_edges["ridge"])
print("can a lift take you from summit to base?", "base" in out_edges["summit"])
