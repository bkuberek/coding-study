"""A hundred clients retrying against a server that is down, with three ways to wait.

Every client's first attempt fails at second 0, and so do its four retries. The waits between
attempts have ceilings of 1, 2, 4 and 8 seconds. Without jitter every client waits exactly the
ceiling, so all hundred retry in the same instant, four times. Full jitter waits a random share
of the ceiling; half jitter waits half the ceiling plus a random share of the other half. The
random numbers come from a seeded generator, whose random() sequence Python keeps the same from
version to version.
"""

import random

CLIENTS, CEILINGS = 100, [1, 2, 4, 8]


def wait(ceiling: float, schedule: str, rng: random.Random) -> float:
    if schedule == "no jitter":
        return ceiling
    if schedule == "full jitter":
        return rng.random() * ceiling
    return ceiling / 2 + rng.random() * ceiling / 2  # half jitter


def retry_times(schedule: str) -> list[float]:
    rng = random.Random(2026)
    times = []
    for _ in range(CLIENTS):
        now = 0.0
        for ceiling in CEILINGS:
            now += wait(ceiling, schedule, rng)
            times.append(now)
    return times


def busiest_tenth(times: list[float]) -> int:
    counts: dict[int, int] = {}
    for time in times:
        tenth = int(time * 10)
        counts[tenth] = counts.get(tenth, 0) + 1
    return max(counts.values())


print("schedule     retries  busiest 0.1 s  earliest retry (s)  last retry (s)")
for schedule in ("no jitter", "full jitter", "half jitter"):
    times = retry_times(schedule)
    print(
        f"{schedule:<11}  {len(times):>7}  {busiest_tenth(times):>13}  "
        f"{min(times):>18.2f}  {max(times):>14.2f}"
    )
