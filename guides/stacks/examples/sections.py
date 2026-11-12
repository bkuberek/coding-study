"""Match every `end` of a timing trace with its `start`, using a stack of the sections still open.

A section that starts inside another one must also end inside it, so the section an `end` closes
is always the one that started most recently and is still open: the top of the stack.
"""

TRACE = [
    (0, "start", "request"),
    (2, "start", "auth"),
    (5, "end", "auth"),
    (6, "start", "query"),
    (9, "start", "cache"),
    (10, "end", "cache"),
    (14, "end", "query"),
    (15, "end", "request"),
]


def durations(trace: list[tuple[int, str, str]], show: bool = False) -> list[tuple[str, int, int]]:
    """Each section's name, how long it took and how many sections were open around it."""
    open_sections: list[tuple[str, int]] = []  # (name, start time); the innermost on top
    finished = []
    for time, kind, name in trace:
        if kind == "start":
            open_sections.append((name, time))
        else:
            if not open_sections:
                raise ValueError(f"end {name}, but no section is open")
            innermost, started = open_sections.pop()
            if innermost != name:
                raise ValueError(f"end {name}, but the innermost open section is {innermost}")
            finished.append((name, time - started, len(open_sections)))
        if show:
            names = [section for section, _ in open_sections]
            print(f"{time:>2} ms  {kind:<5} {name:<7}  open, bottom to top: {names}")
    if open_sections:
        raise ValueError(f"{open_sections[-1][0]} never ended")
    return finished


for name, took, around in durations(TRACE, show=True):
    print(f"{name:<7} took {took:>2} ms inside {around} other section(s)")

broken_traces = {
    "crossed": [(0, "start", "a"), (1, "start", "b"), (2, "end", "a"), (3, "end", "b")],
    "unclosed": [(0, "start", "a"), (1, "start", "b"), (2, "end", "b")],
    "stray end": [(0, "end", "a")],
}
for label, trace in broken_traces.items():
    try:
        durations(trace)
    except ValueError as error:
        print(f"{label}: {error}")
