"""Two threads add 1 to the same number; without a lock, one of the additions is lost.

The threads are simulated, so that the interleaving is the same on every run: each thread is a
generator that yields after every step, and the scheduler lets the two take turns, one step each.
Reading x, adding 1 and writing it back are separate steps, as they are on a real processor.
"""

from collections.abc import Iterator


def add_one(name: str, memory: dict, use_lock: bool) -> Iterator[str]:
    if use_lock:
        while memory["lock"] is not None:
            yield f"{name} waits for the lock"
        memory["lock"] = name  # the test and the set run in one step: nobody runs in between
        yield f"{name} takes the lock"
    value = memory["x"]
    yield f"{name} reads x = {value}"
    memory["x"] = value + 1
    yield f"{name} writes x = {value + 1}"
    if use_lock:
        memory["lock"] = None
        yield f"{name} releases the lock"


def run(use_lock: bool) -> None:
    memory = {"x": 0, "lock": None}
    threads = {name: add_one(name, memory, use_lock) for name in ("A", "B")}
    steps = []
    while threads:
        for name in list(threads):  # take turns: one step of A, then one of B
            try:
                steps.append(next(threads[name]))
            except StopIteration:
                del threads[name]
    print(f"{'with' if use_lock else 'without'} a lock: x = {memory['x']}")
    for step in steps:
        print("  " + step)


run(use_lock=False)
run(use_lock=True)
