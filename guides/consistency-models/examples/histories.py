"""Check small histories of one register, initially 0, against two consistency models.

Each operation is (process, kind, value, start, end), with start and end read off one ideal
clock. A history is sequentially consistent when some single order of all the operations keeps
each process's own order and every read returns the latest write before it. It is linearizable
when such an order also keeps real time: an operation that ended before another started comes
first. The check tries every order, which is fine for four operations.
"""

from itertools import permutations

HISTORIES = {
    "read after the write ends sees it": [("P", "w", 1, 0, 1), ("Q", "r", 1, 2, 3)],
    "read after the write ends misses it": [("P", "w", 1, 0, 1), ("Q", "r", 0, 2, 3)],
    "reads overlap the write": [("P", "w", 1, 0, 4), ("Q", "r", 0, 1, 2), ("Q", "r", 1, 3, 5)],
    "new value, then the old one again": [
        ("P", "w", 1, 0, 1), ("Q", "r", 1, 2, 3), ("Q", "r", 0, 4, 5),
    ],
}


def legal(order: tuple) -> bool:
    value = 0
    for _, kind, v, _, _ in order:
        if kind == "w":
            value = v
        elif v != value:
            return False
    return True


def respects(order: tuple, before) -> bool:
    return all(not before(b, a) for i, a in enumerate(order) for b in order[i + 1 :])


def same_process_first(a, b) -> bool:
    return a[0] == b[0] and a[4] < b[3]


def ended_before_started(a, b) -> bool:
    return a[4] < b[3]


def exists(history: list, before) -> bool:
    return any(legal(o) and respects(o, before) for o in permutations(history))


print(f"{'history':<38} {'sequential':<11} linearizable")
for name, history in HISTORIES.items():
    sequential = exists(history, same_process_first)
    linearizable = exists(history, ended_before_started)
    print(f"{name:<38} {'yes' if sequential else 'no':<11} {'yes' if linearizable else 'no'}")
