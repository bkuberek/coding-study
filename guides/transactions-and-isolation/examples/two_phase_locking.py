"""Strict two-phase locking with a deadlock detector, on two small transactions taking turns.

Reading takes a shared lock; reading "for update" and writing take an exclusive lock, and a
writer that holds the shared lock asks to upgrade it. Locks are held until commit. The two
transactions take turns, one step each; a transaction whose lock is refused waits and tries the
same step on its next turn. When each waits for a lock the other holds, the detector aborts the
younger one (the higher number), which releases its locks and gives up.
"""


def run(title: str, programs: dict[str, list[tuple]], db: dict[str, int]) -> None:
    locks: dict[str, dict[str, str]] = {}  # item -> {transaction: "S" or "X"}
    local: dict[str, dict[str, int]] = {t: {} for t in programs}
    position = dict.fromkeys(programs, 0)
    waiting: dict[str, str] = {}  # transaction -> the transaction it waits for
    events = []

    def grant(t: str, item: str, mode: str) -> str | None:
        """None when granted, else the holder that blocks t."""
        holders = locks.setdefault(item, {})
        others = [h for h in holders if h != t]
        if not others or (mode == "S" and all(holders[h] == "S" for h in others)):
            holders[t] = "X" if mode == "X" or holders.get(t) == "X" else "S"
            return None
        return others[0]

    def finish(t: str, how: str) -> None:
        for holders in locks.values():
            holders.pop(t, None)
        position[t] = len(programs[t])
        waiting.pop(t, None)
        events.append(f"{t} {how}")

    while any(position[t] < len(p) for t, p in programs.items()):
        for t, program in programs.items():
            if position[t] == len(program):
                continue
            op, item, *rest = program[position[t]]
            if op == "commit":
                finish(t, "commits")
                continue
            blocker = grant(t, item, "S" if op == "read" else "X")
            if blocker is None:
                waiting.pop(t, None)
                if op in ("read", "read for update"):
                    local[t][item] = db[item]
                    events.append(f"{t} {op} {item}={db[item]}")
                else:
                    db[item] = local[t][item] + rest[0]
                    events.append(f"{t} writes {item}={db[item]}")
                position[t] += 1
            else:
                if t not in waiting:
                    events.append(f"{t} waits for {blocker}")
                waiting[t] = blocker
                if waiting.get(blocker) == t:
                    finish(max(t, blocker), "is aborted: deadlock")
    print(f"{title}:")
    line = ""
    for event in events:  # wrap between events, never inside one
        if line and len(line) + len(event) + 2 > 92:
            print(f"    {line};")
            line = ""
        line = f"{line}; {event}" if line else event
    print(f"    {line}\n    final: {db}")


def increment(read: str) -> list[tuple]:
    return [(read, "stock"), ("write", "stock", 1), ("commit", None)]


def transfer(source: str, target: str) -> list[tuple]:
    return [
        ("read for update", source),
        ("read for update", target),
        ("write", source, -10),
        ("write", target, 10),
        ("commit", None),
    ]


run("two increments, plain reads", {"T1": increment("read"), "T2": increment("read")}, {"stock": 5})
run(
    "two increments, reads for update",
    {"T1": increment("read for update"), "T2": increment("read for update")},
    {"stock": 5},
)
run(
    "transfers in opposite orders",
    {"T1": transfer("a", "b"), "T2": transfer("b", "a")},
    {"a": 50, "b": 50},
)
run(
    "transfers in the same order",
    {"T1": transfer("a", "b"), "T2": transfer("a", "b")},
    {"a": 50, "b": 50},
)
