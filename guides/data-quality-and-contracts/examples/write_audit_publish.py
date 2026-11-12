"""Write, audit, publish: a batch is checked where readers cannot see it, and published whole or
not at all.

Readers always read the published version. A new batch is written to a staging area, a few
checks run on it, and only a batch that passes them becomes the next published version.
"""

CUSTOMERS = {"c1", "c2", "c3"}
published = {"version": 1, "rows": [("o1", "c1", 900, 470), ("o2", "c2", 450, 480)]}


def audit(rows: list[tuple[str, str, int, int]], now: int) -> list[str]:
    """The failed checks; rows are (order id, customer, amount in cents, event minute)."""
    failed = []
    ids = [row[0] for row in rows]
    if any(not order_id for order_id in ids):
        failed.append("order id missing")
    if len(set(ids)) != len(ids):
        failed.append(f"order id not unique ({len(ids) - len(set(ids))} repeated)")
    unknown = [row[1] for row in rows if row[1] not in CUSTOMERS]
    if unknown:
        failed.append(f"unknown customer {unknown}")
    previous = len(published["rows"])
    if not previous / 2 <= len(rows) <= previous * 2:
        failed.append(f"row count {len(rows)}, previous {previous}")
    newest = max((row[3] for row in rows), default=None)
    if newest is None or now - newest > 120:
        failed.append(f"stale: newest event at minute {newest}, now {now}")
    return failed


def write_audit_publish(staged: list[tuple[str, str, int, int]], now: int) -> None:
    failed = audit(staged, now)
    if failed:
        print(f"blocked: {'; '.join(failed)}")
        return
    published["version"] += 1
    published["rows"] = staged  # one swap: readers see the old version or the new one
    print(f"published version {published['version']} with {len(staged)} rows")


write_audit_publish([("o3", "c1", 1200, 1400), ("o4", "c3", 300, 1410), ("o5", "c2", 80, 1415)],
                    now=1440)
write_audit_publish([("o6", "c2", 500, 2600), ("o6", "c2", 500, 2600), ("o7", "c9", 70, 2610)],
                    now=2880)
print(f"readers see version {published['version']}: {[row[0] for row in published['rows']]}")
