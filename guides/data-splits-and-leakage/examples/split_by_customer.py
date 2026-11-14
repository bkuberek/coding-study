"""Splitting by row against splitting by customer, for a model that recognizes customers.

Each customer places five orders, and whether an order is sent back depends mostly on who placed
it. The model has, in effect, learned to recognize customers: it predicts the label most common for
that customer in its training rows, and the label most common overall for a customer it has never
seen. The question is how well it will do next month, when the customers are new.
"""

import random

rng = random.Random(7)


def shuffled(items) -> list:
    """A Fisher-Yates shuffle built on random(), whose sequence is stable across versions."""
    items = list(items)
    for i in range(len(items) - 1, 0, -1):
        j = int(rng.random() * (i + 1))
        items[i], items[j] = items[j], items[i]
    return items


rows = []  # (customer, returned): 1 when the order was sent back
for customer in range(40):
    habit = 0.85 if rng.random() < 0.4 else 0.1  # the share of orders this customer sends back
    for _ in range(5):
        rows.append((customer, 1 if rng.random() < habit else 0))


def most_common(labels: list[int]) -> int:
    return 1 if 2 * sum(labels) > len(labels) else 0


def accuracy(train: list, test: list) -> float:
    seen: dict[int, list[int]] = {}
    for customer, returned in train:
        seen.setdefault(customer, []).append(returned)
    fallback = most_common([returned for _, returned in train])
    hits = sum((most_common(seen[c]) if c in seen else fallback) == y for c, y in test)
    return hits / len(test)


by_row = shuffled(rows)
row_test, row_train = by_row[:50], by_row[50:]
new_customers = set(shuffled(range(40))[:10])
cust_test = [row for row in rows if row[0] in new_customers]
cust_train = [row for row in rows if row[0] not in new_customers]

print(f"split by row:      accuracy {accuracy(row_train, row_test):.2f}, {len(row_test)} orders")
print(f"split by customer: accuracy {accuracy(cust_train, cust_test):.2f}, {len(cust_test)} orders")
kept = sum(returned == 0 for _, returned in cust_test) / len(cust_test)
print(f"always 'kept':     accuracy {kept:.2f}, the same new customers")
