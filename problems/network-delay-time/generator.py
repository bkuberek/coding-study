"""Seeded networks for network-delay-time.

`n` is the number of nodes (capped at 2000). A random tree of links grows out of the source
`k`, so every node is reachable, with each new node linked from one of the last few nodes
added (long chains, many hops). Extra random links bring the total to about 5n (at most
10^4), creating shortcuts and cycles; travel times are 0 to 100. On about one input in six,
the links into one node are removed, so the answer is -1.
"""

import random

MAX_NODES = 2000
MAX_LINKS = 10**4
MAX_TIME = 100
RECENT = 8


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_NODES)
    source = rng.randint(1, count)
    order = [node for node in range(1, count + 1) if node != source]
    rng.shuffle(order)
    order.insert(0, source)
    links: dict[tuple[int, int], int] = {}
    for index in range(1, count):
        parent = order[rng.randint(max(0, index - RECENT), index - 1)]
        links[(parent, order[index])] = rng.randint(0, MAX_TIME)
    target_links = min(MAX_LINKS, 5 * count, count * (count - 1))
    attempts = 0
    while len(links) < target_links and attempts < 20 * target_links:
        attempts += 1
        u, v = rng.randint(1, count), rng.randint(1, count)
        if u != v and (u, v) not in links:
            links[(u, v)] = rng.randint(0, MAX_TIME)
    if count > 1 and rng.random() < 0.17:
        cut = rng.choice(order[1:])
        links = {pair: w for pair, w in links.items() if pair[1] != cut}
    times = [[u, v, w] for (u, v), w in links.items()]
    rng.shuffle(times)
    return {"times": times, "n": count, "k": source}


def validate(case_input: dict) -> None:
    times, n, k = case_input["times"], case_input["n"], case_input["k"]
    assert 1 <= n <= MAX_NODES and 1 <= k <= n, "node count or source out of range"
    assert len(times) <= MAX_LINKS, "too many links"
    pairs = set()
    for u, v, w in times:
        assert 1 <= u <= n and 1 <= v <= n and u != v, "bad link endpoints"
        assert 0 <= w <= MAX_TIME, "travel time out of range"
        pairs.add((u, v))
    assert len(pairs) == len(times), "a link appears twice"
