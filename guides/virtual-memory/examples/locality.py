"""Reading a table row by row stays on one page for a long time; column by column, it never does.

The table has 512 rows of 512 numbers of 8 bytes each, stored row after row from address 0, so one
row fills exactly one page of 4096 bytes. The program counts how often a read lands on a different
page than the read before it, and how many distinct pages the first 1000 reads touch.
"""

PAGE_SIZE = 4096  # 2 ** 12, so the page number is the address shifted right by 12 bits
ROWS = COLS = 512
ITEM = 8  # bytes per number


def page_of(row: int, col: int) -> int:
    address = (row * COLS + col) * ITEM
    return address >> 12


def walk(addresses: list[int]) -> tuple[int, int]:
    changes, previous = 0, None
    for page in addresses:
        if page != previous:
            changes += 1
            previous = page
    return changes, len(set(addresses[:1000]))


by_rows = [page_of(r, c) for r in range(ROWS) for c in range(COLS)]
by_columns = [page_of(r, c) for c in range(COLS) for r in range(ROWS)]
for name, pages in (("row by row", by_rows), ("column by column", by_columns)):
    changes, early = walk(pages)
    print(
        f"{name:<17} {changes:>6} page changes in {len(pages)} reads; "
        f"the first 1000 reads touch {early} pages"
    )
