HEADER = 8
ALIGN = 8
MIN_BLOCK = 16
POLICIES = ("first-fit", "next-fit", "best-fit")


class Block:
    def __init__(self, start: int, size: int) -> None:
        self.start = start
        self.size = size
        self.used = False
        self.requested = 0


class MemoryAllocator:
    """The heap is a list of blocks in address order, each with its start, its size (header
    included) and whether it is in use. Allocating splits a free block; freeing marks it free and,
    with coalescing or in the buddy system, merges it with its free neighbors. Next fit keeps a
    rover: the address where its next search starts."""

    def __init__(self, heap_size: int) -> None:
        self._heap_size = heap_size
        self._blocks = [Block(0, heap_size)]
        self._coalescing = False
        self._policy = "first-fit"
        self._started = False
        self._rover = 0

    # --- helpers
    def _position(self, start: int) -> int:
        for position, block in enumerate(self._blocks):
            if block.start == start:
                return position
        return -1

    def _block_size(self, size: int) -> int:
        if self._policy == "buddy":
            block = MIN_BLOCK
            while block < size + HEADER:
                block *= 2
            return block
        return HEADER + (size + ALIGN - 1) // ALIGN * ALIGN

    def _choose(self, need: int) -> int:
        """The position of the free block the policy picks, or -1."""
        fits = [i for i, b in enumerate(self._blocks) if not b.used and b.size >= need]
        if not fits:
            return -1
        if self._policy == "next-fit":
            here = self._position(self._rover)
            later = [i for i in fits if i >= here]
            return later[0] if later else fits[0]
        if self._policy in ("best-fit", "buddy"):
            return min(fits, key=lambda i: (self._blocks[i].size, self._blocks[i].start))
        return fits[0]

    def _split(self, position: int, keep: int) -> None:
        block = self._blocks[position]
        rest = Block(block.start + keep, block.size - keep)
        block.size = keep
        self._blocks.insert(position + 1, rest)

    def _merge_with_next(self, position: int) -> None:
        block = self._blocks[position]
        following = self._blocks.pop(position + 1)
        block.size += following.size
        if self._rover == following.start:
            self._rover = block.start

    def _free_buddies(self, position: int) -> None:
        while self._blocks[position].size < self._heap_size:
            block = self._blocks[position]
            buddy = block.start ^ block.size
            other = self._position(buddy)
            partner = self._blocks[other] if other >= 0 else None
            if partner is None or partner.used or partner.size != block.size:
                return
            position = min(position, other)
            self._merge_with_next(position)

    # Level 1
    def allocate(self, size: int) -> int:
        self._started = True
        need = self._block_size(size)
        position = self._choose(need)
        if position < 0:
            return -1
        if self._policy == "buddy":
            while self._blocks[position].size > need:
                self._split(position, self._blocks[position].size // 2)
        elif self._blocks[position].size - need >= MIN_BLOCK:
            self._split(position, need)
        block = self._blocks[position]
        block.used = True
        block.requested = size
        self._rover = (block.start + block.size) % self._heap_size
        return block.start + HEADER

    def free(self, address: int) -> str:
        position = self._position(address - HEADER)
        if position < 0 or not self._blocks[position].used:
            return "invalid"
        self._blocks[position].used = False
        if self._policy == "buddy":
            self._free_buddies(position)
        elif self._coalescing:
            if position + 1 < len(self._blocks) and not self._blocks[position + 1].used:
                self._merge_with_next(position)
            if position > 0 and not self._blocks[position - 1].used:
                self._merge_with_next(position - 1)
        return "ok"

    def heap_map(self) -> list[str]:
        return [f"{b.start} {b.size} {'used' if b.used else 'free'}" for b in self._blocks]

    # Level 2
    def set_coalescing(self, enabled: bool) -> str:
        if self._started:
            return "too-late"
        self._coalescing = enabled
        return "ok"

    def free_report(self) -> list[int]:
        sizes = [b.size for b in self._blocks if not b.used]
        total = sum(sizes)
        largest = max(sizes, default=0)
        fragmentation = 0 if total == 0 else 100 * (total - largest) // total
        return [len(sizes), total, largest, fragmentation]

    # Level 3
    def set_policy(self, policy: str) -> str:
        if policy not in POLICIES and policy != "buddy":
            return "unknown-policy"
        if self._started:
            return "too-late"
        if policy == "buddy" and (self._heap_size & (self._heap_size - 1)) != 0:
            return "bad-size"
        self._policy = policy
        return "ok"

    def compare(self, trace: list[int]) -> list[list[int]]:
        rows = []
        for policy in POLICIES:
            heap = MemoryAllocator(self._heap_size)
            heap.set_coalescing(self._coalescing)
            heap.set_policy(policy)
            addresses: list[int] = []
            failed = 0
            for step in trace:
                if step > 0:
                    addresses.append(heap.allocate(step))
                    failed += addresses[-1] < 0
                elif addresses[-step - 1] >= 0:
                    heap.free(addresses[-step - 1])
            rows.append([failed, *heap.free_report()])
        return rows

    # Level 4
    def wasted(self) -> int:
        return sum(b.size - HEADER - b.requested for b in self._blocks if b.used)
