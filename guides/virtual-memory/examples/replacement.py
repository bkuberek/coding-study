"""Page faults of FIFO, LRU and the optimal policy on one string of page references.

FIFO evicts the page that was loaded the earliest. The optimal policy evicts the page whose next
use is the farthest away, which needs the future, so it can only be run on a recorded string.
LRU is computed the way stack algorithms allow: one pass gives each reference its stack distance,
the position of its page in a list of pages from the most to the least recently used, and a memory
of m frames faults exactly on the references whose distance is larger than m, or which are first
uses.
"""

from collections import deque

REFS = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


def fifo_faults(frames: int) -> int:
    loaded: deque[int] = deque()  # pages in the order they were loaded
    faults = 0
    for page in REFS:
        if page not in loaded:
            faults += 1
            if len(loaded) == frames:
                loaded.popleft()
            loaded.append(page)
    return faults


def next_use(page: int, future: list[int]) -> int:
    """How many references from now the page is used again; never counts as the farthest."""
    return future.index(page) if page in future else len(future)


def optimal_faults(frames: int) -> int:
    resident: set[int] = set()
    faults = 0
    for i, page in enumerate(REFS):
        if page in resident:
            continue
        faults += 1
        if len(resident) == frames:
            future = REFS[i + 1 :]
            distance = {p: next_use(p, future) for p in resident}
            resident.remove(max(sorted(resident), key=distance.__getitem__))
        resident.add(page)
    return faults


def stack_distances() -> list[int | None]:
    stack: list[int] = []  # stack[0] is the most recently used page
    distances: list[int | None] = []
    for page in REFS:
        if page in stack:
            distances.append(stack.index(page) + 1)
            stack.remove(page)
        else:
            distances.append(None)  # a first use faults whatever the memory size
        stack.insert(0, page)
    return distances


distances = stack_distances()
print("references:     ", " ".join(map(str, REFS)))
print("stack distances:", " ".join("-" if d is None else str(d) for d in distances))
print("frames  FIFO  LRU  optimal")
for frames in range(1, 6):
    lru = sum(1 for d in distances if d is None or d > frames)
    print(f"{frames:>6}  {fifo_faults(frames):>4}  {lru:>3}  {optimal_faults(frames):>7}")
