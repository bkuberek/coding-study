"""A pool of equal-sized slots whose free list is kept inside the free slots themselves.

A free slot holds the number of the next free slot, and `head` names the first one, so taking a
slot and giving one back each change one or two numbers, whatever the pool's size. Every slot has
the same size, so no request is ever too large for a free slot: the pool cannot fragment.
"""

END = -1  # marks the last free slot


class Pool:
    def __init__(self, slots: int) -> None:
        # Slot i starts free and points at slot i + 1; the last one ends the list.
        self.slots: list[int | str] = [*range(1, slots), END]
        self.head = 0
        self.used = [False] * slots

    def take(self, value: str) -> int:
        if self.head == END:
            raise MemoryError("the pool is full")
        slot = self.head
        self.head = self.slots[slot]  # the next free slot becomes the head
        self.slots[slot] = value
        self.used[slot] = True
        return slot

    def give_back(self, slot: int) -> None:
        if not self.used[slot]:
            raise ValueError(f"slot {slot} is already free")
        self.slots[slot] = self.head  # the freed slot points at the old head...
        self.head = slot  # ...and becomes the head
        self.used[slot] = False

    def free_list(self) -> list[int]:
        order, slot = [], self.head
        while slot != END:
            order.append(slot)
            slot = self.slots[slot]
        return order


pool = Pool(5)
taken = [pool.take(name) for name in ("a", "b", "c", "d")]
print("taken:", taken, " free list:", pool.free_list())
pool.give_back(1)
pool.give_back(3)
print("after giving back 1 and 3, free list:", pool.free_list())
print("next two takes get slots", pool.take("e"), "and", pool.take("f"))
try:
    pool.give_back(0)
    pool.give_back(0)
except ValueError as error:
    print("double free refused:", error)
