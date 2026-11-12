"""Which changes to a dataset's schema break the people who read it.

A contract lists each column with its type and whether it always has a value. A proposed new
version is compared with it, column by name, from the readers' side: a reader that selects a
column by name, and relies on its type and on it being present, must not be surprised.
"""

CONTRACT = {  # column -> (type, required)
    "order_id": ("string", True),
    "customer_id": ("string", True),
    "amount_cents": ("integer", True),
    "coupon": ("string", False),
    "placed_at": ("timestamp", True),
}
PROPOSED = {
    "order_id": ("string", True),
    "buyer_id": ("string", True),  # customer_id, renamed
    "amount_cents": ("string", True),  # now text, such as "12.50"
    "coupon": ("string", False),
    "placed_at": ("timestamp", False),  # may now be missing
    "channel": ("string", False),
}


def changes(old: dict, new: dict) -> list[tuple[str, str]]:
    found = []
    for column, (kind, required) in old.items():
        if column not in new:
            found.append((f"{column} removed", "breaking"))
            continue
        new_kind, new_required = new[column]
        if new_kind != kind:
            found.append((f"{column} type {kind} -> {new_kind}", "breaking"))
        if required and not new_required:
            found.append((f"{column} may now be missing", "breaking"))
        elif new_required and not required:
            found.append((f"{column} now always present", "compatible"))
    for column in new.keys() - old.keys():
        found.append((f"{column} added", "compatible"))
    return sorted(found)


for change, verdict in changes(CONTRACT, PROPOSED):
    print(f"{verdict:>10}: {change}")
