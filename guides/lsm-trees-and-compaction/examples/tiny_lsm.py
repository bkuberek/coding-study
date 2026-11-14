"""A tiny log-structured merge tree: a memtable, immutable sorted runs, tombstones and compaction.

Writes go to a dictionary in memory, the memtable. When it holds 3 keys it is written out as a
sorted run and emptied; runs are never changed afterwards. A delete writes a tombstone (None).
A read looks in the memtable, then in the runs from newest to oldest, and stops at the first
entry for its key. Compaction merges every run into one, keeping only the newest entry of each
key and dropping tombstones, which is safe here because the merge includes the oldest run.
"""

from bisect import bisect_left

MEMTABLE_LIMIT = 3


class TinyLSM:
    def __init__(self) -> None:
        self.memtable: dict[str, str | None] = {}
        self.runs: list[list[tuple[str, str | None]]] = []  # oldest first
        self.entries_written = 0

    def put(self, key: str, value: str | None) -> None:
        self.memtable[key] = value
        if len(self.memtable) == MEMTABLE_LIMIT:
            run = sorted(self.memtable.items())
            self.runs.append(run)
            self.entries_written += len(run)
            self.memtable = {}

    def delete(self, key: str) -> None:
        self.put(key, None)

    def get(self, key: str) -> tuple[str | None, int]:
        """The value, or None, and how many runs were searched."""
        if key in self.memtable:
            return self.memtable[key], 0
        for searched, run in enumerate(reversed(self.runs), start=1):
            i = bisect_left(run, (key,))
            if i < len(run) and run[i][0] == key:
                return run[i][1], searched
        return None, len(self.runs)

    def compact(self) -> None:
        newest: dict[str, str | None] = {}
        for run in self.runs:  # oldest first, so newer entries overwrite older ones
            newest.update(run)
        merged = sorted((k, v) for k, v in newest.items() if v is not None)
        self.runs = [merged]
        self.entries_written += len(merged)


def show(lsm: TinyLSM, label: str) -> None:
    runs = " | ".join(" ".join(f"{k}={v or '-'}" for k, v in run) for run in lsm.runs)
    print(f"{label:<17} memtable {sorted(lsm.memtable)}  runs: {runs}")


lsm = TinyLSM()
for key, value in [("lime", "3"), ("fig", "7"), ("pear", "2"), ("fig", "8"), ("kiwi", "5")]:
    lsm.put(key, value)
lsm.delete("lime")
show(lsm, "after 6 writes")
for key, value in [("pear", "4"), ("plum", "1"), ("fig", "9")]:
    lsm.put(key, value)
show(lsm, "after 9 writes")
for key in ["fig", "lime", "kiwi", "date"]:
    value, searched = lsm.get(key)
    print(f"get {key:<4} -> {value!s:<4} after searching {searched} run(s)")
print(f"entries written to runs so far: {lsm.entries_written} for 9 writes")
lsm.compact()
show(lsm, "after compaction")
for key in ["fig", "lime", "kiwi", "date"]:
    value, searched = lsm.get(key)
    print(f"get {key:<4} -> {value!s:<4} after searching {searched} run(s)")
print(f"entries written to runs in all: {lsm.entries_written} for 9 writes")
