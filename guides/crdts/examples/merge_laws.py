"""Which merge functions make replicas agree, whatever the network does with their messages?

Three replicas each make one local change, then pass their states around: every replica sends
to every other, in every possible order, and the last message is sent twice. A merge that is
commutative, associative and idempotent ends with all three replicas in the same state every
time; the others lose changes or count them twice. The laws are checked on the three states.
"""

from itertools import permutations

MERGES = {  # name: (merge, the three replicas' states after their local changes)
    "union of sets": (lambda mine, theirs: mine | theirs, [{"ana"}, {"ben"}, {"cy"}]),
    "larger number": (max, [3, 9, 4]),
    "take theirs": (lambda mine, theirs: theirs, [3, 9, 4]),
    "concatenate": (lambda mine, theirs: mine + theirs, [("ana",), ("ben",), ("cy",)]),
}
SENDS = [(s, t) for s in range(3) for t in range(3) if s != t]


def show(state) -> str:  # sets print in a fixed order, whatever the hash seed
    return repr(sorted(state)) if isinstance(state, set) else repr(state)


def laws(merge, x, y, z) -> str:
    return " ".join([
        "commutative" if merge(x, y) == merge(y, x) else "-",
        "associative" if merge(merge(x, y), z) == merge(x, merge(y, z)) else "-",
        "idempotent" if merge(x, x) == x else "-",
    ])


print(f"{len(list(permutations(SENDS)))} orders of {len(SENDS)} messages, the last one sent twice")
for name, (merge, start) in MERGES.items():
    finals = set()
    for order in permutations(SENDS):
        states = list(start)
        for source, target in [*order, order[-1]]:  # the last message arrives twice
            states[target] = merge(states[target], states[source])
        agree = len({show(s) for s in states}) == 1
        finals.add("agree on " + show(states[0]) if agree else "disagree")
    print(f"{name:<14} {laws(merge, *start)}")
    for outcome in sorted(finals):
        print(f"{'':<14} {outcome}")

guests = [{"milk"}, {"milk"}]  # two replicas of a set, both holding milk
guests[1] = guests[1] - {"milk"}  # replica 1 removes milk
guests[1] = guests[1] | guests[0]  # then merges replica 0's state, which still has milk
print("remove, then merge by union:", show(guests[1]))
