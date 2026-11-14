"""Replay a fixed history of three processes and stamp every event two ways.

A Lamport clock is one counter per process: +1 on every event, and on a receive first jump past
the message's stamp. A vector clock keeps one counter per process: an event adds one to its own
entry, and a receive first takes the larger of each entry from the message. Comparing the
stamps of two events shows what each kind of clock can and cannot tell.
"""

PROCESSES = ["P", "Q", "R"]
HISTORY = [  # (event, process, kind, message): in an order the events could have happened
    ("p1", "P", "local", None),
    ("q1", "Q", "local", None),
    ("r1", "R", "local", None),
    ("p2", "P", "send", "m1"),
    ("q2", "Q", "receive", "m1"),
    ("p3", "P", "local", None),
    ("q3", "Q", "send", "m2"),
    ("r2", "R", "receive", "m2"),
    ("r3", "R", "send", "m3"),
    ("p4", "P", "receive", "m3"),
]

lamport = {p: 0 for p in PROCESSES}
vector = {p: (0, 0, 0) for p in PROCESSES}
in_flight: dict[str, tuple[int, tuple[int, ...]]] = {}  # message -> the stamps it carries
stamps: dict[str, tuple[int, tuple[int, ...]]] = {}

for event, p, kind, message in HISTORY:
    if kind == "receive":
        carried_lamport, carried_vector = in_flight.pop(message)
        lamport[p] = max(lamport[p], carried_lamport)
        vector[p] = tuple(max(a, b) for a, b in zip(vector[p], carried_vector))
    lamport[p] += 1
    own = PROCESSES.index(p)
    vector[p] = tuple(n + 1 if i == own else n for i, n in enumerate(vector[p]))
    stamps[event] = (lamport[p], vector[p])
    if kind == "send":
        in_flight[message] = stamps[event]
    print(f"{event} on {p} ({kind:<7}) Lamport {lamport[p]}  vector {list(vector[p])}")


def happened_before(a: str, b: str) -> bool:
    va, vb = stamps[a][1], stamps[b][1]
    return va != vb and all(x <= y for x, y in zip(va, vb))


for a, b in [("p1", "r2"), ("r1", "p4"), ("p3", "q3"), ("p3", "r3")]:
    if happened_before(a, b):
        order = "before"
    elif happened_before(b, a):
        order = "after"
    else:
        order = "concurrent"
    print(f"{a} vs {b}: Lamport {stamps[a][0]} vs {stamps[b][0]}, vectors say {order}")
