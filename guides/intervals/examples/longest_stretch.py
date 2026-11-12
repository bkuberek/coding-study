"""A channel airs segments [start, end) in minutes, some of them at the same time. Find the longest
stretch during which something was on air without a break."""

from collections.abc import Iterator

Interval = tuple[int, int]


def show(interval: Interval) -> str:
    start, end = interval
    return f"[{start:>2}, {end:>2})"


def unbroken_runs(segments: list[Interval]) -> Iterator[Interval]:
    """Yield the stretches without a break, from left to right, printing each step."""
    ordered = sorted(segments)
    run_start, run_end = ordered[0]
    print(f"{show(ordered[0])} opens a run")
    for start, end in ordered[1:]:
        if start <= run_end:
            run_end = max(run_end, end)  # a segment may end inside the run
            print(f"{show((start, end))} joins it: {show((run_start, run_end))}")
        else:
            print(f"{show((start, end))} starts after {run_end}: a new run opens")
            yield run_start, run_end
            run_start, run_end = start, end
    yield run_start, run_end


segments = [(30, 45), (0, 10), (8, 20), (12, 15), (20, 26), (40, 52), (60, 70)]
start, end = max(unbroken_runs(segments), key=lambda run: run[1] - run[0])
print(f"longest unbroken stretch: [{start}, {end}), {end - start} minutes")
