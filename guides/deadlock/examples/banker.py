"""Dijkstra's banker: grant a loan only when the state after it is still safe.

The banker has 10 units of one resource. Each process declared in advance the most it will ever
hold at once, its maximum claim. A state is safe when some order lets every process, one at a
time, receive the rest of its claim, finish and pay back everything it holds.
"""

CAPITAL = 10
CLAIMS = {"P": 8, "Q": 4, "R": 9}


def safe_order(loans: dict[str, int]) -> list[str] | None:
    """An order in which every process can finish, or None when there is none."""
    free = CAPITAL - sum(loans.values())
    waiting = dict.fromkeys(loans, True)
    order = []
    while waiting:
        ready = [p for p in sorted(waiting) if CLAIMS[p] - loans[p] <= free]
        if not ready:
            return None
        process = ready[0]
        free += loans[process]  # it finishes and pays back what it held
        order.append(process)
        del waiting[process]
    return order


def request(loans: dict[str, int], process: str, units: int) -> dict[str, int]:
    after = {**loans, process: loans[process] + units}
    order = safe_order(after)
    verdict = f"granted, safe order {' '.join(order)}" if order else "refused: unsafe"
    free = CAPITAL - sum(after.values())
    print(f"{process} asks for {units} more, {free} would stay free: {verdict}")
    return after if order else loans


loans = {"P": 3, "Q": 2, "R": 2}
start = safe_order(loans) or []
print(f"loans {loans}, {CAPITAL - sum(loans.values())} free, safe order: {' '.join(start)}")
loans = request(loans, "R", 1)
loans = request(loans, "P", 1)
