"""Seeded ticket piles for reconstruct-itinerary.

`n` is the number of tickets (capped at 1000). A random walk of `n` flights starting at "JFK"
over a pool of airports (2 to about sqrt(n) + 3 random codes, plus "JFK") produces the
tickets, so a trip using all of them always exists; the tickets are then shuffled. Walks
revisit airports often, which creates many choice points, repeated tickets, and dead ends
that a purely greedy walk would run into.
"""

import random
import string

MAX_TICKETS = 1000
START = "JFK"


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_TICKETS)
    pool_size = rng.randint(2, int(count**0.5) + 3)
    airports = {START}
    while len(airports) < pool_size + 1:
        airports.add("".join(rng.choice(string.ascii_uppercase) for _ in range(3)))
    pool = sorted(airports)
    walk = [START]
    for _ in range(count):
        walk.append(rng.choice([airport for airport in pool if airport != walk[-1]]))
    tickets = [[a, b] for a, b in zip(walk, walk[1:])]
    rng.shuffle(tickets)
    return {"tickets": tickets}


def validate(case_input: dict) -> None:
    tickets = case_input["tickets"]
    assert 1 <= len(tickets) <= MAX_TICKETS, "ticket count out of range"
    for a, b in tickets:
        for code in (a, b):
            assert len(code) == 3 and all(ch in string.ascii_uppercase for ch in code), "bad airport code"
        assert a != b, "a ticket returns to its own airport"
    # An Eulerian trail from START exists: degree balance plus connectivity from START.
    balance: dict[str, int] = {}
    for a, b in tickets:
        balance[a] = balance.get(a, 0) + 1
        balance[b] = balance.get(b, 0) - 1
    surplus = {airport: value for airport, value in balance.items() if value != 0}
    assert not surplus or (len(surplus) == 2 and surplus.get(START) == 1 and sorted(surplus.values()) == [-1, 1]), "degrees do not allow a trip from JFK"
    reached = {START}
    stack = [START]
    outgoing: dict[str, list[str]] = {}
    for a, b in tickets:
        outgoing.setdefault(a, []).append(b)
    while stack:
        for nxt in outgoing.get(stack.pop(), []):
            if nxt not in reached:
                reached.add(nxt)
                stack.append(nxt)
    assert all(a in reached for a, _ in tickets), "some tickets cannot be reached from JFK"
