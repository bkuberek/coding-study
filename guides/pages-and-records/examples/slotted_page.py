"""A slotted page: records at the end, a slot array at the start, and free space in between.

The page is a bytearray of 128 bytes. Its first 4 bytes hold two offsets: where the slot array
ends ("lower") and where the records start ("upper"). Each slot is 4 bytes: the record's offset
and length. A record's id is its slot number, which never changes while the record lives, even
when compaction moves the record's bytes.
"""

import struct

PAGE_SIZE = 128
HEADER = struct.Struct(">HH")  # lower, upper
SLOT = struct.Struct(">HH")  # offset, length; length 0 marks a free slot


class SlottedPage:
    def __init__(self) -> None:
        self.data = bytearray(PAGE_SIZE)
        HEADER.pack_into(self.data, 0, HEADER.size, PAGE_SIZE)

    def _bounds(self) -> tuple[int, int]:
        return HEADER.unpack_from(self.data, 0)

    def _slot(self, n: int) -> tuple[int, int]:
        return SLOT.unpack_from(self.data, HEADER.size + n * SLOT.size)

    def slot_count(self) -> int:
        lower, _ = self._bounds()
        return (lower - HEADER.size) // SLOT.size

    def free_space(self) -> int:
        lower, upper = self._bounds()
        return upper - lower

    def insert(self, record: bytes) -> int | None:
        lower, upper = self._bounds()
        reuse = next((n for n in range(self.slot_count()) if self._slot(n)[1] == 0), None)
        needed = len(record) + (0 if reuse is not None else SLOT.size)
        if needed > upper - lower:
            return None
        upper -= len(record)
        self.data[upper : upper + len(record)] = record
        n = reuse if reuse is not None else self.slot_count()
        SLOT.pack_into(self.data, HEADER.size + n * SLOT.size, upper, len(record))
        if reuse is None:
            lower += SLOT.size
        HEADER.pack_into(self.data, 0, lower, upper)
        return n

    def read(self, n: int) -> bytes | None:
        offset, length = self._slot(n)
        return bytes(self.data[offset : offset + length]) if length else None

    def delete(self, n: int) -> None:
        SLOT.pack_into(self.data, HEADER.size + n * SLOT.size, 0, 0)

    def compact(self) -> None:
        """Move the live records to the end of the page; their slot numbers stay the same."""
        lower, _ = self._bounds()
        live = [(n, self.read(n)) for n in range(self.slot_count())]
        upper = PAGE_SIZE
        for n, record in live:
            if record is not None:
                upper -= len(record)
                self.data[upper : upper + len(record)] = record
                SLOT.pack_into(self.data, HEADER.size + n * SLOT.size, upper, len(record))
        HEADER.pack_into(self.data, 0, lower, upper)


def show(page: SlottedPage, label: str) -> None:
    lower, upper = page._bounds()
    slots = []
    for n in range(page.slot_count()):
        offset, length = page._slot(n)
        slots.append(f"{n}@{offset}+{length}" if length else f"{n}:free")
    print(f"{label:<28} lower={lower:<3} upper={upper:<3} free={page.free_space():<3}", *slots)


page = SlottedPage()
show(page, "empty page")
for text in ["ada:analytical engine", "grace:compiler", "edsger:shortest paths"]:
    page.insert(text.encode())
page.insert(b"barbara:abstract data types and clu")
show(page, "after four inserts")

record = b"frances:program optimization"
print(f"insert of {len(record)} bytes -> {page.insert(record)}")
page.delete(1)
show(page, "after deleting slot 1")
print(f"insert of {len(record)} bytes -> {page.insert(record)} (the free bytes are in two pieces)")
page.compact()
show(page, "after compaction")
print(f"insert of {len(record)} bytes -> slot {page.insert(record)}")
show(page, "after the insert")
print("slot 0 still reads", page.read(0).decode(), "and slot 3", page.read(3).decode())
