"""Is a history serializable? Build its dependency graph and look for a cycle.

A history is written as in Berenson and others' critique of the ANSI isolation levels: r1[x] is a
read of x by transaction 1, w2[y] a write of y by transaction 2, c1 the commit of transaction 1.
Two actions conflict when they come from different transactions, touch the same item, and at
least one is a write. Each conflicting pair adds an edge from the earlier action's transaction to
the later one's. With no cycle, the transactions in an order that follows every edge form an
equivalent serial history; with a cycle, no serial order explains the history.
"""

import re
from graphlib import CycleError, TopologicalSorter

HISTORIES = {
    "lost update (H4)": "r1[x] r2[x] w2[x] c2 w1[x] c1",
    "inconsistent analysis (H1)": "r1[x] w1[x] r2[x] r2[y] c2 r1[y] w1[y] c1",
    "interleaved, but harmless": "r1[x] w1[x] r2[x] w2[x] r1[y] w1[y] c1 r2[y] w2[y] c2",
    "write skew (H5)": "r1[x] r1[y] r2[x] r2[y] w1[y] w2[x] c1 c2",
}


def analyse(history: str) -> None:
    actions = re.findall(r"([rw])(\d)\[(\w)\]", history)
    edges: dict[tuple[str, str], str] = {}
    for i, (op1, t1, item1) in enumerate(actions):
        for op2, t2, item2 in actions[i + 1 :]:
            if t1 != t2 and item1 == item2 and "w" in (op1, op2):
                why = f"{op1}{t1}[{item1}] before {op2}{t2}[{item2}]"
                edges.setdefault((f"T{t1}", f"T{t2}"), why)
    graph: dict[str, set[str]] = {f"T{t}": set() for _, t, _ in actions}
    for (a, b), why in sorted(edges.items()):
        graph[b].add(a)
        print(f"    {a} -> {b}  ({why})")
    try:
        order = list(TopologicalSorter(graph).static_order())
        print(f"    no cycle: equivalent to running {', then '.join(order)}")
    except CycleError as error:
        cycle = error.args[1][:-1]  # the first node is repeated at the end
        start = cycle.index(min(cycle))  # start the report at T1 whatever node was found first
        cycle = [*cycle[start:], *cycle[:start], cycle[start]]
        print(f"    cycle {' -> '.join(cycle)}: not serializable")


for name, history in HISTORIES.items():
    print(f"{name}: {history}")
    analyse(history)
