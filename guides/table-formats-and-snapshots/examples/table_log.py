"""A table kept as a log of numbered commits over immutable files, with optimistic writers.

Commit n records which files it adds and removes. A writer commits by creating entry n + 1, which
succeeds only if no one created it first. When it loses that race it reads the commits it missed,
checks that the files it removes are still in the table, and tries again at the next number.
"""


class TableLog:
    def __init__(self) -> None:
        self.entries: dict[int, dict[str, list[str]]] = {}

    def put_if_absent(self, version: int, adds: list[str], removes: list[str]) -> bool:
        if version in self.entries:
            return False
        self.entries[version] = {"adds": adds, "removes": removes}
        return True

    def latest(self) -> int:
        return max(self.entries, default=-1)

    def files_at(self, version: int) -> list[str]:
        """Time travel: replay the log up to a version."""
        live: set[str] = set()
        for number in range(version + 1):
            live -= set(self.entries[number]["removes"])
            live |= set(self.entries[number]["adds"])
        return sorted(live)


def commit(log: TableLog, name: str, base: int, adds: list[str], removes: list[str]) -> None:
    version = base + 1
    while not log.put_if_absent(version, adds, removes):
        missing = [path for path in removes if path not in log.files_at(log.latest())]
        if missing:
            print(f"{name}: version {version} taken, conflict: {', '.join(missing)} already gone")
            return
        print(f"{name}: version {version} taken, nothing it removes changed, retrying")
        version = log.latest() + 1
    print(f"{name}: committed version {version}")


log = TableLog()
log.put_if_absent(0, ["a.data", "b.data"], [])
# Three writers all read version 0, then commit in this order.
commit(log, "append c", base=0, adds=["c.data"], removes=[])
commit(log, "compact a+b", base=0, adds=["ab.data"], removes=["a.data", "b.data"])
commit(log, "delete b", base=0, adds=[], removes=["b.data"])
for version in range(log.latest() + 1):
    print(f"version {version}: {log.files_at(version)}")
