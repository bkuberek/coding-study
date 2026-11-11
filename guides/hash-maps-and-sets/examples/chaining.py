"""A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.

It hashes with zlib.crc32, which is the same in every run, so the output is too; Python's own
hash() of a str changes from run to run."""

import zlib

MAX_LOAD = 0.75


class ChainedMap:
    def __init__(self, buckets: int = 4) -> None:
        self.buckets: list[list[tuple[str, int]]] = [[] for _ in range(buckets)]
        self.size = 0
        self.moved = 0  # entries copied by every resize so far

    def bucket_of(self, key: str) -> list[tuple[str, int]]:
        return self.buckets[zlib.crc32(key.encode()) % len(self.buckets)]

    def put(self, key: str, value: int) -> None:
        chain = self.bucket_of(key)
        for position, (stored, _) in enumerate(chain):
            if stored == key:  # a collision is fine: compare the keys themselves
                chain[position] = (key, value)
                return
        chain.append((key, value))
        self.size += 1
        if self.size / len(self.buckets) > MAX_LOAD:
            self.resize(2 * len(self.buckets))

    def get(self, key: str) -> int | None:
        for stored, value in self.bucket_of(key):
            if stored == key:
                return value
        return None

    def resize(self, buckets: int) -> None:
        entries = [entry for chain in self.buckets for entry in chain]
        self.buckets = [[] for _ in range(buckets)]
        for key, value in entries:
            self.bucket_of(key).append((key, value))
        self.moved += len(entries)


ages = ChainedMap()
for number, name in enumerate(["ada", "bo", "cy", "di"], start=30):
    ages.put(name, number)
    print(f"put {name}: {ages.size} entries in {len(ages.buckets)} buckets")
print("get('cy') =", ages.get("cy"), "| get('zed') =", ages.get("zed"))

for count in (1_000, 100_000):
    table = ChainedMap()
    for number in range(count):
        table.put(f"key{number}", number)
    longest = max(len(chain) for chain in table.buckets)
    print(
        f"{count:>7} puts: {len(table.buckets):>6} buckets, "
        f"{table.moved / count:.2f} moves per put, longest chain {longest}"
    )
