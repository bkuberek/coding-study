"""A print shop has one press. Each job takes some hours and is promised by an hour of the day,
counted from opening. Earliest deadline first keeps the worst lateness as small as it can be."""

from itertools import permutations
from typing import NamedTuple


class Job(NamedTuple):
    name: str
    hours: int
    due: int


def lateness(order: list[Job]) -> list[int]:
    """How late each job finishes, in the order run: negative means early."""
    clock, late = 0, []
    for job in order:
        clock += job.hours
        late.append(clock - job.due)
    return late


def worst(order: list[Job]) -> int:
    return max(lateness(order))


def best_worst_of_every_order(jobs: list[Job]) -> int:
    return min(worst(list(order)) for order in permutations(jobs))


def show(order: list[Job]) -> str:
    pairs = zip(order, lateness(order), strict=True)
    return ", ".join(f"{job.name} {late:+d}" for job, late in pairs)


ALL_FIT = [Job("brochure", 4, 4), Job("stickers", 1, 7), Job("catalog", 5, 12), Job("labels", 2, 9)]
OVERBOOKED = [
    Job("poster", 5, 6),
    Job("flyers", 2, 7),
    Job("cards", 2, 8),
    Job("menus", 1, 9),
    Job("banner", 3, 10),
]

for jobs in (ALL_FIT, OVERBOOKED):
    shortest = sorted(jobs, key=lambda job: job.hours)
    earliest_due = sorted(jobs, key=lambda job: job.due)
    print(f"shortest first:  {show(shortest)}; worst {worst(shortest):+d}")
    print(f"earliest due:    {show(earliest_due)}; worst {worst(earliest_due):+d}")
    print(f"best of every order: worst {best_worst_of_every_order(jobs):+d}")
