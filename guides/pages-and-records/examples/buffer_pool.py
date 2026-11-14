"""A buffer pool: a few page frames in memory in front of a disk, with least-recently-used eviction.

Every request for a page is a hit when the page is already in a frame, and a read from disk
otherwise. A changed page is "dirty": it is written back to disk only when it leaves its frame,
or when the pool is flushed.
"""

from collections import OrderedDict


class BufferPool:
    def __init__(self, frames: int) -> None:
        self.frames = frames
        self.pages: OrderedDict[int, bool] = OrderedDict()  # page number -> dirty
        self.hits = self.reads = self.writes = 0

    def get(self, page: int, *, change: bool = False) -> None:
        if page in self.pages:
            self.hits += 1
            self.pages.move_to_end(page)
        else:
            if len(self.pages) == self.frames:
                _, dirty = self.pages.popitem(last=False)  # the least recently used page
                if dirty:
                    self.writes += 1
            self.reads += 1
            self.pages[page] = False
        if change:
            self.pages[page] = True

    def flush(self) -> None:
        for page, dirty in self.pages.items():
            if dirty:
                self.writes += 1
                self.pages[page] = False


def run(label: str, requests: list[int], frames: int = 3, changes: frozenset = frozenset()):
    pool = BufferPool(frames)
    for i, page in enumerate(requests):
        pool.get(page, change=i in changes)
    pool.flush()
    print(
        f"{label:<34} {len(requests):>2} requests  {pool.hits:>2} hits"
        f"  {pool.reads:>2} reads  {pool.writes:>2} writes"
    )


run("hot pages 1 and 2, now and then 3", [1, 2, 1, 3, 1, 2, 1, 2, 3, 1, 2, 1])
run("scan of 4 pages, twice", [1, 2, 3, 4, 1, 2, 3, 4])
run("scan of 3 pages, twice", [1, 2, 3, 1, 2, 3])
run("page 7 changed 5 times", [7, 7, 7, 7, 7], changes=frozenset(range(5)))
run("5 pages changed once each", [1, 2, 3, 4, 5], changes=frozenset(range(5)))
