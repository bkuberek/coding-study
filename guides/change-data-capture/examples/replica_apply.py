"""A replica that starts from a snapshot and catches up on one ordered change log.

The replica stores its rows and the log position it has applied up to, and changes both in the
same step. The snapshot sets that position, and every event at or below it is skipped, so events
the snapshot already holds, and events delivered again after a reconnect, change nothing.
"""

LOG = [  # (log position, op, key, row after the change); "d" carries no row
    (10, "c", "1", {"plan": "free"}),
    (20, "c", "2", {"plan": "free"}),
    (30, "u", "1", {"plan": "pro"}),
    (40, "u", "1", {"plan": "team"}),
    (50, "d", "2", None),
]


class Replica:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, str]] = {}
        self.position = 0

    def load_snapshot(self, rows: dict[str, dict[str, str]], position: int) -> None:
        self.rows, self.position = dict(rows), position

    def apply(self, lsn: int, op: str, key: str, row: dict[str, str] | None) -> str:
        if lsn <= self.position:
            return "skipped"
        if op == "d":
            self.rows.pop(key, None)
        else:
            self.rows[key] = row or {}
        self.position = lsn  # a real replica commits the rows and the position together
        return "applied"


def plans(rows: dict[str, dict[str, str]]) -> dict[str, str]:
    return {key: row["plan"] for key, row in sorted(rows.items())}


replica = Replica()
replica.load_snapshot({"1": {"plan": "pro"}, "2": {"plan": "free"}}, position=30)
print("snapshot as of 30:", plans(replica.rows))
for event in LOG:  # the reader started before the snapshot finished, at position 10
    print(f"  lsn {event[0]}: {replica.apply(*event)}")
for event in LOG[3:]:  # the connection dropped, and the log delivers again from 40
    print(f"  lsn {event[0]} again: {replica.apply(*event)}")
print("replica:", plans(replica.rows), "at position", replica.position)

naive: dict[str, dict[str, str]] = {}
for lsn, op, key, row in LOG + LOG[:1]:
    if op == "c" and key in naive:
        print(f"without positions, lsn {lsn} again: insert of key {key} fails, duplicate key")
    elif op == "d":
        naive.pop(key, None)
    else:
        naive[key] = row or {}
