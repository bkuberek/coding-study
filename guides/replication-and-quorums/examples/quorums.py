"""Read and write quorums over five replicas, each holding a (version, value) pair.

A write goes to w replicas and a read asks r replicas and keeps the highest version. When
r + w > 5, every read set shares a replica with every write set, so a read always meets the
latest write. The last part shows what a quorum does not do: order two writes made at once.
"""

from itertools import combinations

N = 5
REPLICAS = range(N)

for w, r in [(3, 3), (5, 1), (2, 2)]:
    pairs = [(ws, rs) for ws in combinations(REPLICAS, w) for rs in combinations(REPLICAS, r)]
    missed = sum(1 for ws, rs in pairs if not set(ws) & set(rs))
    print(f"w={w} r={r}: r + w = {w + r}, {missed} of {len(pairs)} read sets miss a write set")

store = {i: (1, "blue") for i in REPLICAS}


def write(replicas: tuple[int, ...], version: int, value: str) -> None:
    for i in replicas:
        store[i] = (version, value)


def read(replicas: tuple[int, ...]) -> list[tuple[int, str]]:
    newest = max(store[i][0] for i in replicas)
    return sorted({store[i] for i in replicas if store[i][0] == newest})


write((0, 1, 2), 2, "green")
print("after one write to 0, 1, 2; read from 2, 3, 4:", read((2, 3, 4)))

# Two clients both read version 2, then both write version 3, to overlapping quorums.
write((0, 1, 2), 3, "red")
write((2, 3, 4), 3, "white")  # replica 2 keeps the write that reached it last
print("after two writes at once; read from 0, 3, 4:  ", read((0, 3, 4)))
