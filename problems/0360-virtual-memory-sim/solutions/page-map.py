from collections import OrderedDict


class VirtualMemory:
    """One address space: a page table from page to frame, an optional TLB kept in
    least-recently-used order, and, once demand paging is on, a frame table with the state each
    replacement policy needs: the load order for FIFO, the use order for LRU, and a use bit per
    frame and a hand for the clock. Every translation is one reference in a history, which the
    working set reads.

    Splitting an address is a shift and a mask, because the page size is a power of two.
    """

    def __init__(self, page_size: int) -> None:
        self._size = page_size
        self._shift = page_size.bit_length() - 1
        self._table: dict[int, int] = {}
        self._faults = 0
        self._tlb: OrderedDict[int, int] | None = None
        self._tlb_entries = 0
        self._hits = 0
        self._misses = 0
        self._frames = 0
        self._policy = ""
        self._owner: list[int] = []
        self._loaded: OrderedDict[int, None] = OrderedDict()
        self._recent: OrderedDict[int, None] = OrderedDict()
        self._use: list[bool] = []
        self._hand = 0
        self._history: list[int] = []

    # Level 1
    def split(self, address: int) -> list[int]:
        return [address >> self._shift, address & (self._size - 1)]

    def map_page(self, page: int, frame: int) -> bool:
        new = page not in self._table
        self._table[page] = frame
        self._invalidate(page)
        return new

    def unmap_page(self, page: int) -> bool:
        if page not in self._table:
            return False
        del self._table[page]
        self._invalidate(page)
        return True

    def translate(self, address: int) -> int:
        page, offset = self.split(address)
        self._history.append(page)
        frame = self._frame_of(page)
        return -1 if frame is None else frame * self._size + offset

    def faults(self) -> int:
        return self._faults

    # Level 2
    def enable_tlb(self, entries: int) -> None:
        self._tlb = OrderedDict()
        self._tlb_entries = entries
        self._hits = self._misses = 0

    def flush_tlb(self) -> None:
        if self._tlb is not None:
            self._tlb.clear()

    def tlb_hits(self) -> int:
        return self._hits

    def tlb_misses(self) -> int:
        return self._misses

    # Level 3
    def use_frames(self, count: int, policy: str) -> None:
        self._frames, self._policy = count, policy
        self._table.clear()
        self.flush_tlb()
        self._faults = self._hits = self._misses = 0
        self._owner = [-1] * count
        self._use = [False] * count
        self._loaded.clear()
        self._recent.clear()
        self._hand = 0
        self._history.clear()

    def resident(self) -> list[int]:
        return sorted(self._table)

    # Level 4
    def walk(self, address: int, entry_bytes: int) -> list[int]:
        per_table = self._size // entry_bytes
        page, offset = self.split(address)
        return [page // per_table, page % per_table, offset]

    def table_bytes(self, address_bits: int, entry_bytes: int) -> list[int]:
        pages = 1 << (address_bits - self._shift)
        per_table = self._size // entry_bytes
        directory = pages // per_table * entry_bytes
        tables = len({page // per_table for page in self._table})
        return [pages * entry_bytes, directory + tables * self._size]

    def working_set(self, window: int) -> list[int]:
        return sorted(set(self._history[-window:]))

    def thrashing(self, window: int) -> bool:
        return self._frames > 0 and len(self.working_set(window)) > self._frames

    # Translation
    def _frame_of(self, page: int) -> int | None:
        if self._tlb is not None:
            if page in self._tlb:
                self._hits += 1
                self._tlb.move_to_end(page)
                self._touch(page)
                return self._tlb[page]
            self._misses += 1
        frame = self._table.get(page)
        if frame is None:
            self._faults += 1
            if self._frames == 0:
                return None
            frame = self._load(page)
        self._touch(page)
        if self._tlb is not None:
            if len(self._tlb) == self._tlb_entries:
                self._tlb.popitem(last=False)
            self._tlb[page] = frame
        return frame

    def _invalidate(self, page: int) -> None:
        if self._tlb is not None:
            self._tlb.pop(page, None)

    def _touch(self, page: int) -> None:
        if self._frames == 0:
            return
        self._recent.pop(page, None)
        self._recent[page] = None
        self._use[self._table[page]] = True

    def _load(self, page: int) -> int:
        if len(self._table) < self._frames:
            frame = len(self._table)
        else:
            frame = self._victim_frame()
            victim = self._owner[frame]
            del self._table[victim]
            del self._loaded[victim]
            del self._recent[victim]
            self._invalidate(victim)
        self._table[page] = frame
        self._owner[frame] = page
        self._loaded[page] = None
        return frame

    def _victim_frame(self) -> int:
        if self._policy == "fifo":
            return self._table[next(iter(self._loaded))]
        if self._policy == "lru":
            return self._table[next(iter(self._recent))]
        while self._use[self._hand]:
            self._use[self._hand] = False
            self._hand = (self._hand + 1) % self._frames
        frame = self._hand
        self._hand = (self._hand + 1) % self._frames
        return frame
