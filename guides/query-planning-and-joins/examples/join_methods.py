"""Three ways to compute the same equi-join, and the work each one does.

The query pairs each order with its customer: orders.customer = customers.id. The nested loop
reads every customer again for each order. The hash join puts the customers in a hash table once,
then looks up each order. The sort-merge join sorts both inputs on the join key, then walks them
side by side. All three return the same rows.
"""

customers = [(3, "ana"), (1, "bo"), (6, "cy"), (2, "di"), (5, "ed"), (4, "flo")]  # (id, name)
CUSTOMER_OF_ORDER = [2, 5, 2, 7, 1, 5, 3, 2, 6, 1, 4, 5, 2, 3]
orders = list(zip(range(101, 115), CUSTOMER_OF_ORDER, strict=True))  # (id, customer)


def nested_loop() -> tuple[list, int]:
    out, compared = [], 0
    for order_id, customer in orders:
        for cid, name in customers:
            compared += 1
            if customer == cid:
                out.append((order_id, name))
    return out, compared


def hash_join() -> tuple[list, int]:
    table: dict[int, list[str]] = {}
    for cid, name in customers:  # build
        table.setdefault(cid, []).append(name)
    out = [(order_id, name) for order_id, customer in orders for name in table.get(customer, [])]
    return out, len(customers) + len(orders)  # inserts plus lookups


def sort_merge() -> tuple[list, int]:
    left, right = sorted(orders, key=lambda o: o[1]), sorted(customers)
    out, steps, i, j = [], 0, 0, 0
    while i < len(left) and j < len(right):
        steps += 1
        if left[i][1] < right[j][0]:
            i += 1
        elif left[i][1] > right[j][0]:
            j += 1
        else:  # customer ids are unique, so each order matches at most this one
            out.append((left[i][0], right[j][1]))
            i += 1
    return out, steps


results = {}
for name, method, unit in [
    ("nested loop", nested_loop, "comparisons"),
    ("hash join", hash_join, "inserts and lookups"),
    ("sort-merge", sort_merge, "merge steps, after sorting 14 and 6 rows"),
]:
    rows, work = method()
    results[name] = sorted(rows)
    print(f"{name:<12} {len(rows)} rows  {work:>3} {unit}")
print("same rows from all three:", len({tuple(r) for r in results.values()}) == 1)
print("order 104 names customer 7, who does not exist, so no method returns it")
