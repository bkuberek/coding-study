"""One trail map stored three ways: an edge list, an adjacency list and an adjacency matrix."""

from collections import defaultdict

huts = ["alder", "birch", "cedar", "dune", "ember", "fern", "gorse"]
trails = [  # the edge list: one pair per trail, walkable both ways
    ("alder", "birch"),
    ("alder", "cedar"),
    ("cedar", "dune"),
    ("ember", "fern"),
]

# Adjacency list: every hut gets an entry, even gorse with no trail, and each trail is stored twice.
neighbors: dict[str, list[str]] = {hut: [] for hut in huts}
for a, b in trails:
    neighbors[a].append(b)
    neighbors[b].append(a)
for hut, near in neighbors.items():
    print(f"{hut:>5}: {near}")

# Adjacency matrix: row i, column j holds 1 when huts i and j share a trail.
index = {hut: position for position, hut in enumerate(huts)}
matrix = [[0] * len(huts) for _ in huts]
for a, b in trails:
    matrix[index[a]][index[b]] = 1
    matrix[index[b]][index[a]] = 1
print("matrix row of cedar:", matrix[index["cedar"]])
print("trail between birch and cedar?", matrix[index["birch"]][index["cedar"]] == 1)

degrees = {hut: len(near) for hut, near in neighbors.items()}
print("degrees:", degrees)
print(f"sum of degrees: {sum(degrees.values())} = 2 x {len(trails)} trails")
print(f"matrix cells: {len(huts) ** 2}, adjacency list entries: {sum(degrees.values())}")

# A defaultdict builds the same lists with less code, and brings two surprises.
lazy: defaultdict[str, list[str]] = defaultdict(list)
for a, b in trails:
    lazy[a].append(b)
    lazy[b].append(a)
print("gorse in the defaultdict?", "gorse" in lazy)
print("neighbors of zinnia:", lazy["zinnia"], "| keys now:", len(lazy))
