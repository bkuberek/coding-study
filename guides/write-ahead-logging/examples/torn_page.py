"""A torn page: power fails during a page write, and a full page image in the log repairs it.

A page here is 16 bytes, written as four 4-byte sectors, one sector at a time: the page's LSN,
eight bytes of data, and a checksum of the first twelve bytes. Redo applies a log record only
when the page's LSN is older than the record's, so a page whose first sector already carries the
new LSN is skipped, although the rest of it never reached the disk. A copy of the whole page,
logged with the first change after a checkpoint, replaces the torn page.
"""

import zlib

SECTOR = 4


def make_page(lsn: int, data: bytes) -> bytes:
    head = lsn.to_bytes(4, "big") + data
    return head + zlib.crc32(head).to_bytes(4, "big")


def describe(page: bytes) -> str:
    ok = zlib.crc32(page[:12]).to_bytes(4, "big") == page[12:]
    return f"LSN {int.from_bytes(page[:4], 'big')}, data {page[4:12].decode()}, checksum ok: {ok}"


def redo(page: bytes, lsn: int, offset: int, data: bytes) -> bytes:
    if int.from_bytes(page[:4], "big") >= lsn:
        return page  # the page looks as new as the record: skip it
    body = bytearray(page[4:12])
    body[offset : offset + len(data)] = data
    return make_page(lsn, bytes(body))


old = make_page(7, b"qty=0010")
new = make_page(9, b"qty=0042")  # LSN 9 changed the 4 bytes at offset 4 of the data
torn = new[: 2 * SECTOR] + old[2 * SECTOR :]  # power failed after two of the four sectors
print("before the write:  ", describe(old))
print("after a whole write:", describe(new))
print("torn write:        ", describe(torn))
print("redo of LSN 9:     ", describe(redo(torn, 9, 4, b"0042")))
image = new  # the whole page, logged with LSN 9, the first change after the last checkpoint
print("logged image:      ", describe(image))
