"""Revenue per day, answered by a batch job and by a stream processor over the same orders.

Each order has the day it was placed and the hour, counted from Monday 00:00, at which it reached
the pipeline. The batch job for a day runs once, when the day ends, over what has arrived by then.
The stream processor updates a running total the moment each order arrives.
"""

ORDERS = [  # (order id, day placed, amount in cents, hour it arrived)
    ("o1", "mon", 1200, 9),
    ("o2", "mon", 800, 17),
    ("o3", "tue", 1500, 26),
    ("o4", "mon", 300, 27),  # placed on Monday by a phone that was offline until Tuesday
    ("o5", "tue", 700, 40),
]
DAY_ENDS = {"mon": 24, "tue": 48}


def batch_job(day: str, run_at_hour: int) -> int:
    """One run: read every order of the day that has arrived by now, and add them up."""
    arrived = [order for order in ORDERS if order[3] <= run_at_hour]
    return sum(cents for _, placed, cents, _ in arrived if placed == day)


class RunningTotals:
    """A stream processor: it keeps one total per day and updates it for each order."""

    def __init__(self) -> None:
        self.totals: dict[str, int] = {}

    def on_order(self, placed: str, cents: int) -> int:
        self.totals[placed] = self.totals.get(placed, 0) + cents
        return self.totals[placed]


print("batch, each day's job at the end of the day:")
for day, end in DAY_ENDS.items():
    print(f"  hour {end}: {day} = {batch_job(day, end)}")
print(f"  hour 50, monday's job run again: mon = {batch_job('mon', 50)}")

print("stream, one update per order:")
stream = RunningTotals()
for order_id, placed, cents, hour in ORDERS:
    print(f"  hour {hour}: {order_id} -> {placed} = {stream.on_order(placed, cents)}")
