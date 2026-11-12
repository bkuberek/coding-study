"""A priority queue on heapq: the most urgent case first, and equal urgency in arrival order.

heapq compares whole entries. A (priority, payload) pair falls back to comparing payloads when
the priorities tie, which orders ties by payload instead of by arrival, or fails for payloads
that cannot be compared. A running counter between the two settles every tie by arrival."""

import heapq
import itertools

arrivals = [  # (urgency, case): 1 is the most urgent
    (2, {"name": "Rosa", "issue": "sprained ankle"}),
    (1, {"name": "Tomas", "issue": "chest pain"}),
    (2, {"name": "Amara", "issue": "deep cut"}),
    (3, {"name": "Lin", "issue": "sore throat"}),
    (1, {"name": "Kofi", "issue": "breathing trouble"}),
]

naive: list[tuple[int, dict[str, str]]] = []
try:
    for entry in arrivals:
        heapq.heappush(naive, entry)
except TypeError as error:
    print("(urgency, case) pairs fail on a tie:", error)

queue: list[tuple[int, int, dict[str, str]]] = []
order = itertools.count()  # 0, 1, 2, ...: never equal, so the cases are never compared
for urgency, case in arrivals:
    heapq.heappush(queue, (urgency, next(order), case))

while queue:
    urgency, arrived, case = heapq.heappop(queue)
    print(f"urgency {urgency}, arrival {arrived}: {case['name']}, {case['issue']}")
