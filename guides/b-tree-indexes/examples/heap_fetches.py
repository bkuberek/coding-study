"""An index finds row ids; the rows themselves still live on table pages, which must be read.

A table of 100,000 rows with 100 rows per page, so 1,000 pages: row i sits on page i // 100.
Two columns are indexed. order_id is i, so it follows the order of the rows on disk. customer
is (i * 7919) % 100,000, which visits every value once in a scrambled order, so neighbouring
values sit on unrelated pages. Each query asks for 1,000 consecutive key values, 1% of the rows.
"""

ROWS, PER_PAGE = 100_000, 100
order_id = {i: i for i in range(ROWS)}  # key -> row number, the index's leaf entries
customer = {(i * 7919) % ROWS: i for i in range(ROWS)}


def index_scan(index: dict[int, int], low: int, high: int) -> tuple[int, int]:
    """Fetch rows in key order; reading a page again only when it differs from the last one."""
    reads, last = 0, None
    pages = []
    for key in range(low, high + 1):
        page = index[key] // PER_PAGE
        pages.append(page)
        if page != last:
            reads, last = reads + 1, page
    return reads, len(set(pages))


print(f"full scan reads every page: {ROWS // PER_PAGE:,} pages, in order")
for name, index in [("order_id", order_id), ("customer", customer)]:
    reads, distinct = index_scan(index, 40_000, 40_999)
    print(
        f"index on {name:<8}: 1,000 rows, {reads:>5,} page reads in key order,"
        f" {distinct:>4} distinct pages"
    )
