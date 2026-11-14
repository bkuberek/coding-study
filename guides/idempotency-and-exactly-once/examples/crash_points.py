"""A consumer credits 50 points for one message, and may crash at any point of its work.

The queue redelivers a message until it is acknowledged, so a crash before the ack means the
message comes again, to a fresh consumer. Only the database survives a crash, and a commit
writes all of its changes or none. Three consumers handle the same message, `credit c-17`:

- ack first: acknowledge, then credit;
- credit first: credit, then acknowledge;
- dedupe: in one commit, credit and record the operation id c-17, unless it is already recorded;
  then acknowledge.
"""


class Crash(Exception):
    pass


def deliver(strategy: str, crash_at: str | None) -> int:
    db = {"points": 0, "done": frozenset()}
    acked = False
    while not acked:  # the queue redelivers until it hears an ack
        try:
            if strategy == "ack first":
                acked = True
                if crash_at == "after ack":
                    raise Crash
                db = {**db, "points": db["points"] + 50}
            elif strategy == "credit first":
                db = {**db, "points": db["points"] + 50}
                if crash_at == "after commit":
                    raise Crash
                acked = True
            else:  # dedupe
                if crash_at == "before commit":
                    raise Crash
                if "c-17" not in db["done"]:  # the check and the credit commit together
                    db = {"points": db["points"] + 50, "done": db["done"] | {"c-17"}}
                if crash_at == "after commit":
                    raise Crash
                acked = True
        except Crash:
            crash_at = None  # the next consumer does not crash
    return db["points"]


CASES = [
    ("ack first", None), ("ack first", "after ack"),
    ("credit first", None), ("credit first", "after commit"),
    ("dedupe", None), ("dedupe", "before commit"), ("dedupe", "after commit"),
]
for strategy, crash_at in CASES:
    points = deliver(strategy, crash_at)
    print(f"{strategy:<12} crash {crash_at or 'never':<13} -> {points:>3} points")
