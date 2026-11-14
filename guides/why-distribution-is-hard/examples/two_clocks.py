"""Two machines log what they do, each stamping lines with its own clock, and the logs are merged.

Machine B's clock runs 250 ms behind machine A's. A request takes 40 ms to reach B, B answers
5 ms later, and the reply takes 30 ms to come back. Sorted by the clocks' readings, B receives
the request before A has sent it.
"""

CLOCK_ERROR = {"A": 0, "B": -250}  # what each clock reads minus the true time, in ms

history = [  # (true time in ms, machine, what it did), in the order it happened
    (1000, "A", "sends request #7"),
    (1040, "B", "receives request #7"),
    (1045, "B", "sends reply to #7"),
    (1075, "A", "receives reply to #7"),
]


def reading(true_time: int, machine: str) -> int:
    return true_time + CLOCK_ERROR[machine]


print("merged log, sorted by each line's clock reading:")
for true_time, machine, what in sorted(history, key=lambda line: reading(line[0], line[1])):
    print(f"  {reading(true_time, machine):>4} ms  {machine}  {what}")
print("what happened, in order:")
for true_time, machine, what in history:
    print(f"  {true_time:>4} ms  {machine}  {what}")
