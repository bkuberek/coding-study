"""Four jobs that all arrive at time 0, run under three scheduling policies.

For each policy the program prints the runs, written job:start-end, and the average waiting,
turnaround and response times. Then it tries all 24 orders of the jobs, to check that running the
shortest job first gives the smallest average waiting time.
"""

from collections import deque
from fractions import Fraction
from itertools import permutations

BURSTS = {"A": 6, "B": 8, "C": 7, "D": 3}  # ticks of CPU time each job needs

Run = tuple[str, int, int]  # (job, start, end)


def one_after_another(order: list[str]) -> list[Run]:
    """Run each job to the end, in the given order: no job is ever stopped."""
    runs, now = [], 0
    for job in order:
        runs.append((job, now, now + BURSTS[job]))
        now += BURSTS[job]
    return runs


def round_robin(quantum: int) -> list[Run]:
    """Each job runs for at most `quantum` ticks, then goes to the back of the queue."""
    queue, left, runs, now = deque(BURSTS), dict(BURSTS), [], 0
    while queue:
        job = queue.popleft()
        ran = min(quantum, left[job])
        runs.append((job, now, now + ran))
        now += ran
        left[job] -= ran
        if left[job] > 0:
            queue.append(job)
    return runs


def averages(runs: list[Run]) -> tuple[Fraction, Fraction, Fraction]:
    first_start: dict[str, int] = {}
    completion: dict[str, int] = {}
    for job, start, end in runs:
        first_start.setdefault(job, start)
        completion[job] = end
    n = len(BURSTS)
    turnaround = Fraction(sum(completion.values()), n)  # every job arrived at 0
    waiting = Fraction(sum(completion[job] - BURSTS[job] for job in BURSTS), n)
    response = Fraction(sum(first_start.values()), n)
    return waiting, turnaround, response


policies = {
    "first come, first served": one_after_another(list(BURSTS)),
    "shortest job first": one_after_another(sorted(BURSTS, key=BURSTS.get)),
    "round robin, quantum 4": round_robin(4),
}
for name, runs in policies.items():
    waiting, turnaround, response = averages(runs)
    print(name)
    print("  " + " ".join(f"{job}:{start}-{end}" for job, start, end in runs))
    print(
        f"  waiting {float(waiting):.2f}, turnaround {float(turnaround):.2f}, "
        f"response {float(response):.2f}"
    )

orders = [list(order) for order in permutations(BURSTS)]
best = min(orders, key=lambda order: averages(one_after_another(order))[0])
print(
    f"best average waiting of {len(orders)} orders: {' '.join(best)}, "
    f"{float(averages(one_after_another(best))[0]):.2f}"
)
