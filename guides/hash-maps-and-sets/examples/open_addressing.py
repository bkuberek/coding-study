"""Open addressing with linear probing: a key that finds its home slot taken tries the next one.

Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.
"""

SLOTS = 8
EMPTY = None
DELETED = "<deleted>"  # a tombstone: the slot is free to reuse, but a search goes on past it


class ProbingSet:
    def __init__(self) -> None:
        self.slots: list[int | str | None] = [EMPTY] * SLOTS

    def probe(self, key: int):
        """The slots to try for `key`: its home slot, then the next ones, wrapping around."""
        home = key % SLOTS
        return [(home + step) % SLOTS for step in range(SLOTS)]

    def add(self, key: int) -> list[int]:
        tried = []
        reusable = None
        for slot in self.probe(key):
            tried.append(slot)
            if self.slots[slot] == key:
                return tried
            if self.slots[slot] == DELETED and reusable is None:
                reusable = slot
            if self.slots[slot] is EMPTY:
                self.slots[slot if reusable is None else reusable] = key
                return tried
        raise RuntimeError("full: a real table resizes long before this")

    def contains(self, key: int) -> tuple[bool, list[int]]:
        tried = []
        for slot in self.probe(key):
            tried.append(slot)
            if self.slots[slot] is EMPTY:
                return False, tried
            if self.slots[slot] == key:
                return True, tried
        return False, tried

    def remove(self, key: int, tombstone: bool = True) -> None:
        for slot in self.probe(key):
            if self.slots[slot] == key:
                self.slots[slot] = DELETED if tombstone else EMPTY
                return


table = ProbingSet()
for key in (3, 11, 19, 6):
    print(f"add {key:>2}: home {key % SLOTS}, tried slots {table.add(key)}")
print("slots:", table.slots)

table.remove(11)
print("remove 11 with a tombstone:", table.slots)
print("contains 19?", table.contains(19))

broken = ProbingSet()
for key in (3, 11, 19):
    broken.add(key)
broken.remove(11, tombstone=False)
print("remove 11 by emptying its slot, contains 19?", broken.contains(19))
