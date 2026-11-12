"""Two ways to copy a table's changes: polling it by a last-updated time, and reading its log.

A tiny database keeps a table and, like a real one, writes every change to a log first, at a
position that only grows. Polling asks the table "which rows changed since my last poll?";
reading the log asks "which changes come after the position I stopped at?".
"""


class Database:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, str]] = {}
        self.updated_at: dict[str, int] = {}
        self.log: list[dict] = []  # one change event per write, in commit order

    def write(self, time: int, op: str, key: str, row: dict[str, str] | None = None) -> None:
        before = self.rows.get(key)
        self.log.append({"lsn": 10 * (len(self.log) + 1), "op": op, "key": key,
                         "before": before, "after": row})
        if row is None:
            del self.rows[key], self.updated_at[key]
        else:
            self.rows[key], self.updated_at[key] = row, time


def poll(db: Database, since: int) -> list[str]:
    return [f"{key} {row['plan']}" for key, row in db.rows.items() if db.updated_at[key] > since]


db = Database()
db.write(1, "c", "1", {"name": "ana", "plan": "free"})
db.write(2, "c", "2", {"name": "ben", "plan": "free"})
print("poll at time 2:", poll(db, since=0))
db.write(3, "u", "1", {"name": "ana", "plan": "pro"})
db.write(4, "u", "1", {"name": "ana", "plan": "team"})
db.write(5, "d", "2")
print("poll at time 5:", poll(db, since=2))
print("the log from position 0:")
for event in db.log:
    before = event["before"] and event["before"]["plan"]
    after = event["after"] and event["after"]["plan"]
    print(f"  lsn {event['lsn']}: {event['op']} key {event['key']}, plan {before} -> {after}")
