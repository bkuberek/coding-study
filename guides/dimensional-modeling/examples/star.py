"""A tiny star schema: revenue by product category, as it was and as it is.

The product dimension keeps category as a type 2 attribute: when the desk lamp moved from Lighting
to Home office on 15 April, its row was closed and a new row, with a new surrogate key, began.
Each sale points at the product row that was valid when it happened.
"""

OPEN_END = 99991231
PRODUCTS = [  # (surrogate key, business key, name, category, valid from, valid to)
    (1, "P3", "monitor arm", "Home office", 20260101, OPEN_END),
    (2, "P7", "desk lamp", "Lighting", 20260101, 20260415),
    (3, "P7", "desk lamp", "Home office", 20260415, OPEN_END),
]
SALES = [  # (date, product surrogate key, amount): the fact table
    (20260310, 2, 40),
    (20260320, 1, 120),
    (20260402, 2, 35),
    (20260420, 3, 45),
    (20260505, 1, 110),
]
BY_KEY = {row[0]: row for row in PRODUCTS}
CURRENT = {row[1]: row for row in PRODUCTS if row[5] == OPEN_END}


def revenue_by_category(as_it_is: bool) -> dict[str, int]:
    totals: dict[str, int] = {}
    for _, key, amount in SALES:
        product = BY_KEY[key]
        if as_it_is:  # a type 1 view: follow the business key to the current row
            product = CURRENT[product[1]]
        totals[product[3]] = totals.get(product[3], 0) + amount
    return dict(sorted(totals.items()))


def key_at(business_key: str, date: int) -> int:
    """The surrogate key of the row valid on a date: valid from <= date < valid to."""
    for key, product, _, _, valid_from, valid_to in PRODUCTS:
        if product == business_key and valid_from <= date < valid_to:
            return key
    return -1


print("as it was (type 2):", revenue_by_category(as_it_is=False))
print("as it is (type 1): ", revenue_by_category(as_it_is=True))
late = key_at("P7", 20260410)
print(f"late sale of P7 dated 20260410: key {late} ({BY_KEY[late][3]}), current key {CURRENT['P7'][0]}")
