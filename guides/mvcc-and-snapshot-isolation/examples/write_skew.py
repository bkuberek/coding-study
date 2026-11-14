"""Snapshot isolation by the definition: each transaction reads the committed state as of its start,
keeps its writes to itself, and commits only if no transaction that committed after its start
wrote an item it also wrote (first committer wins).

Copying the whole committed state at each start is the definition made literal, not how a store
does it; it is enough to watch what snapshot isolation allows and what it refuses.
"""


class SnapshotStore:
    def __init__(self, data: dict[str, int]) -> None:
        self.committed = dict(data)
        self.clock = 0
        self.history: list[tuple[int, set[str]]] = []  # (commit time, items written)

    def begin(self) -> dict:
        self.clock += 1
        return {"start": self.clock, "snapshot": dict(self.committed), "writes": {}}

    def read(self, t: dict, item: str) -> int:
        return t["writes"].get(item, t["snapshot"][item])

    def write(self, t: dict, item: str, value: int) -> None:
        t["writes"][item] = value

    def commit(self, t: dict) -> str:
        for when, items in self.history:
            if when > t["start"] and items & t["writes"].keys():
                return "aborted: first committer wins"
        self.clock += 1
        self.committed.update(t["writes"])
        self.history.append((self.clock, set(t["writes"])))
        return "committed"


def withdraw(store: SnapshotStore, t: dict, account: str, amount: int, cover: bool) -> str:
    """Withdraw if the couple's two balances stay positive in total, as this snapshot shows them."""
    x, y = store.read(t, "x"), store.read(t, "y")
    if x + y - amount <= 0:
        return "refused"
    store.write(t, account, store.read(t, account) - amount)
    if cover:  # also write the balance it only read, so a concurrent withdrawal conflicts
        other = "y" if account == "x" else "x"
        store.write(t, other, store.read(t, other))
    return "ok"


def skew(cover: bool) -> str:
    store = SnapshotStore({"x": 70, "y": 80})
    t1, t2 = store.begin(), store.begin()
    w1, w2 = withdraw(store, t1, "x", 100, cover), withdraw(store, t2, "y", 100, cover)
    c1, c2 = store.commit(t1), store.commit(t2)
    total = store.committed["x"] + store.committed["y"]
    return f"T1 {w1}, {c1} | T2 {w2}, {c2} | x + y = {total}"


print("lost update: two transactions add 1 to a counter of 5")
store = SnapshotStore({"counter": 5})
t1, t2 = store.begin(), store.begin()
for t in (t1, t2):
    store.write(t, "counter", store.read(t, "counter") + 1)
print("    T1:", store.commit(t1), "| T2:", store.commit(t2))
t2 = store.begin()
store.write(t2, "counter", store.read(t2, "counter") + 1)
print("    T2 again:", store.commit(t2), "| counter =", store.committed["counter"])


print("write skew: x = 70, y = 80, each transaction withdraws 100 from one account")
print("    " + skew(cover=False))

print("one after the other: T1 commits before T2 begins")
store = SnapshotStore({"x": 70, "y": 80})
t1 = store.begin()
w1 = withdraw(store, t1, "x", 100, False)
c1 = store.commit(t1)
t2 = store.begin()
w2 = withdraw(store, t2, "y", 100, False)
print(f"    T1 {w1}, {c1} | T2 {w2} | x + y = {store.committed['x'] + store.committed['y']}")

print("write skew, covered: each withdrawal also writes the balance it only read")
print("    " + skew(cover=True))

print("phantom: tasks may add up to 8 hours; two transactions each add a 1-hour task")
store = SnapshotStore({"task1": 4, "task2": 3})
t1, t2 = store.begin(), store.begin()
for t, new in ((t1, "task3"), (t2, "task4")):
    if sum(store.read(t, k) for k in t["snapshot"]) + 1 <= 8:  # the sum over a predicate
        store.write(t, new, 1)
c1, c2 = store.commit(t1), store.commit(t2)
print(f"    T1 {c1} | T2 {c2} | hours = {sum(store.committed.values())}")
