"""The press is overbooked, so some jobs will be late. Keep as many on time as possible: take the
jobs by deadline, and whenever the kept jobs no longer fit, give up the longest of them. A max-heap
of the kept jobs' hours finds the longest one in O(log n)."""

import heapq
from collections.abc import Iterable
from itertools import combinations, count, product
from typing import NamedTuple


class Job(NamedTuple):
    name: str
    hours: int
    due: int


def by_due(jobs: Iterable[Job]) -> list[Job]:
    return sorted(jobs, key=lambda job: job.due)


def all_on_time(jobs: Iterable[Job]) -> bool:
    clock = 0
    for job in by_due(jobs):
        clock += job.hours
        if clock > job.due:
            return False
    return True


class OnTimePlan:
    """The most jobs that can be on time among those taken so far, taken in deadline order."""

    def __init__(self) -> None:
        self._kept: list[tuple[int, int, Job]] = []  # (-hours, arrival, job): heapq is a min-heap
        self._arrivals = count()
        self.hours = 0

    def take(self, job: Job) -> Job | None:
        """Take the next job by deadline; return the job given up to keep the rest on time."""
        heapq.heappush(self._kept, (-job.hours, next(self._arrivals), job))
        self.hours += job.hours
        if self.hours <= job.due:
            return None
        _, _, longest = heapq.heappop(self._kept)
        self.hours -= longest.hours
        return longest

    def jobs(self) -> list[Job]:
        return by_due(job for _, _, job in self._kept)


def most_on_time(jobs: list[Job]) -> list[Job]:
    plan = OnTimePlan()
    for job in by_due(jobs):
        plan.take(job)
    return plan.jobs()


def never_give_up(jobs: list[Job]) -> list[Job]:
    """By deadline, keep each job that still fits, and never give one up."""
    kept: list[Job] = []
    for job in by_due(jobs):
        if sum(other.hours for other in kept) + job.hours <= job.due:
            kept.append(job)
    return kept


def most_by_brute_force(jobs: list[Job]) -> int:
    return max(
        size
        for size in range(len(jobs) + 1)
        for chosen in combinations(jobs, size)
        if all_on_time(chosen)
    )


jobs = [
    Job("poster", 5, 6),
    Job("flyers", 2, 7),
    Job("cards", 2, 8),
    Job("menus", 1, 9),
    Job("banner", 3, 10),
]
plan = OnTimePlan()
for job in by_due(jobs):
    given_up = plan.take(job)
    if given_up is None:
        print(f"take {job.name:<6} -> {plan.hours:>2} h, due {job.due:>2}: fits")
        continue
    before = plan.hours + given_up.hours
    print(f"take {job.name:<6} -> {before:>2} h, due {job.due:>2}: give up {given_up.name}", end="")
    print(f", {given_up.hours} h, leaving {plan.hours} h")
print("on time:", [job.name for job in plan.jobs()], "| all on time:", all_on_time(plan.jobs()))
print("never giving up a job keeps", [job.name for job in never_give_up(jobs)])
print("most of any set:", most_by_brute_force(jobs))

small = [
    [Job(str(i), hours, due) for i, (hours, due) in enumerate(zip(hours_list, dues, strict=True))]
    for hours_list in product((1, 2, 3), repeat=4)
    for dues in product((2, 4, 6), repeat=4)
]
wrong = sum(len(most_on_time(jobs)) != most_by_brute_force(jobs) for jobs in small)
print(f"{len(small)} inputs of 4 jobs: the heap rule falls short on {wrong}")
