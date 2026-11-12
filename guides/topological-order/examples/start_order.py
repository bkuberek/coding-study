"""A start order for services that need other services running first: Kahn's algorithm and DFS.

`needs[s]` lists the services that must start before s. Ties are broken by name, so that the output
is the same on every run."""

import heapq

needs = {
    "config": [],
    "metrics": [],
    "db": ["config"],
    "cache": ["config"],
    "auth": ["db", "cache"],
    "web": ["auth"],
}


def kahn(needs: dict[str, list[str]], trace: bool = False) -> list[str]:
    unlocks: dict[str, list[str]] = {service: [] for service in needs}
    waiting_for = {service: len(before) for service, before in needs.items()}
    for service, before in needs.items():
        for dependency in before:
            unlocks[dependency].append(service)
    ready = [service for service, count in waiting_for.items() if count == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        service = heapq.heappop(ready)
        order.append(service)
        for later in unlocks[service]:
            waiting_for[later] -= 1
            if waiting_for[later] == 0:
                heapq.heappush(ready, later)
        if trace:
            print(f"  start {service:<8} ready: {sorted(ready)}")
    return order


def dfs_order(needs: dict[str, list[str]]) -> list[str]:
    unlocks: dict[str, list[str]] = {service: [] for service in needs}
    for service, before in needs.items():
        for dependency in before:
            unlocks[dependency].append(service)
    finished: list[str] = []
    seen: set[str] = set()

    def visit(service: str) -> None:
        seen.add(service)
        for later in unlocks[service]:
            if later not in seen:
                visit(later)
        finished.append(service)  # everything that must come after it is already finished

    for service in sorted(needs):
        if service not in seen:
            visit(service)
    return finished[::-1]


print("Kahn's algorithm:")
order = kahn(needs, trace=True)
print("order:", order)
print("DFS, reversed finish order:", dfs_order(needs))

needs["config"] = ["auth"]  # a mistake: config now waits for auth, which waits for config
stuck = kahn(needs)
print("with a cycle, Kahn's algorithm starts only", stuck)
print("never ready:", sorted(set(needs) - set(stuck)))
