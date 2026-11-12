from bisect import bisect_left


class _Transaction:
    __slots__ = ("commit_time", "ins", "outs", "reads", "serializable", "start", "state", "writes")

    def __init__(self, start: int, serializable: bool) -> None:
        self.start = start
        self.serializable = serializable
        self.state = "active"
        self.commit_time = 0
        self.writes: dict[str, str] = {}
        self.reads: set[str] = set()
        self.ins: set[int] = set()
        self.outs: set[int] = set()


class MvccStore:
    """Every key keeps a chain of committed versions, oldest first, each stamped with the commit
    time of its writer and the id of that writer (0 for a put). A transaction buffers its writes
    until it commits, so the chains only ever hold committed data, and a read is a binary search
    for the newest stamp before the reader's start.

    Serializable transactions also leave their reads behind, even after they commit, and every
    read-write antidependency between two of them is kept as a pair of edges. An edge stops
    counting as soon as either end aborts.
    """

    def __init__(self) -> None:
        self._clock = 0
        self._stamps: dict[str, list[int]] = {}
        self._values: dict[str, list[str]] = {}
        self._writers: dict[str, list[int]] = {}
        self._transactions: dict[int, _Transaction] = {}
        self._readers: dict[str, set[int]] = {}

    # Level 1
    def put(self, key: str, value: str) -> int:
        self._clock += 1
        self._append(key, value, self._clock, 0)
        return self._clock

    def begin(self) -> int:
        return self._start(serializable=False)

    def read(self, tx: int, key: str) -> str:
        reader = self._active(tx)
        if reader is None:
            return ""
        if key in reader.writes:
            return reader.writes[key]
        if reader.serializable and not self._record_read(tx, reader, key):
            return ""
        stamps = self._stamps.get(key, [])
        visible = bisect_left(stamps, reader.start)
        return self._values[key][visible - 1] if visible else ""

    def versions(self, key: str) -> list[str]:
        stamps = self._stamps.get(key, [])
        values = self._values.get(key, [])
        return [f"{stamp}:{value}" for stamp, value in zip(reversed(stamps), reversed(values))]

    # Level 2
    def write(self, tx: int, key: str, value: str) -> bool:
        writer = self._active(tx)
        if writer is None:
            return False
        if writer.serializable and not self._record_write(tx, writer, key):
            return False
        writer.writes[key] = value
        return True

    def commit(self, tx: int) -> str:
        t = self._active(tx)
        if t is None:
            return "not-active"
        if any(self._stamps.get(key, [0])[-1] > t.start for key in t.writes):
            t.state = "aborted"
            return "write-conflict"
        if t.serializable and self._live(t.ins) and self._live(t.outs):
            t.state = "aborted"
            return "dangerous-structure"
        self._clock += 1
        t.state, t.commit_time = "committed", self._clock
        for key, value in t.writes.items():
            self._append(key, value, self._clock, tx)
        return "committed"

    def abort(self, tx: int) -> bool:
        t = self._active(tx)
        if t is None:
            return False
        t.state = "aborted"
        return True

    def status(self, tx: int) -> str:
        t = self._transactions.get(tx)
        return t.state if t is not None else "unknown"

    # Level 3
    def begin_serializable(self) -> int:
        return self._start(serializable=True)

    def antidependencies(self, tx: int) -> list[str]:
        t = self._transactions.get(tx)
        if t is None or t.state == "aborted":
            return []
        return [f"in:{other}" for other in sorted(self._live(t.ins))] + [
            f"out:{other}" for other in sorted(self._live(t.outs))
        ]

    # Level 4
    def horizon(self) -> int:
        starts = [t.start for t in self._transactions.values() if t.state == "active"]
        return min(starts, default=self._clock)

    def vacuum(self) -> list[str]:
        limit = self.horizon()
        removed = []
        for key in sorted(self._stamps):
            stamps = self._stamps[key]
            keep_from = bisect_left(stamps, limit + 1) - 1
            if keep_from <= 0:
                continue
            removed += [f"{key}@{stamp}" for stamp in stamps[:keep_from]]
            del stamps[:keep_from]
            del self._values[key][:keep_from]
            del self._writers[key][:keep_from]
        return removed

    # Helpers
    def _start(self, serializable: bool) -> int:
        self._clock += 1
        self._transactions[self._clock] = _Transaction(self._clock, serializable)
        return self._clock

    def _active(self, tx: int) -> _Transaction | None:
        t = self._transactions.get(tx)
        return t if t is not None and t.state == "active" else None

    def _append(self, key: str, value: str, stamp: int, writer: int) -> None:
        self._stamps.setdefault(key, []).append(stamp)
        self._values.setdefault(key, []).append(value)
        self._writers.setdefault(key, []).append(writer)

    def _serializable(self, tx: int) -> _Transaction | None:
        t = self._transactions.get(tx)
        return t if t is not None and t.serializable and t.state != "aborted" else None

    def _live(self, ids: set[int]) -> set[int]:
        return {other for other in ids if self._transactions[other].state != "aborted"}

    def _record_read(self, tx: int, reader: _Transaction, key: str) -> bool:
        """The reader misses every version committed after it began and every write still
        buffered by an active transaction: each such writer gets an edge from the reader."""
        stamps = self._stamps.get(key, [])
        newer = self._writers.get(key, [])[bisect_left(stamps, reader.start) :]
        committed = [w for w in newer if self._serializable(w) is not None]
        if any(self._live(self._transactions[w].outs) for w in committed):
            reader.state = "aborted"
            return False
        buffered = [
            other
            for other, t in self._transactions.items()
            if other != tx and t.serializable and t.state == "active" and key in t.writes
        ]
        self._readers.setdefault(key, set()).add(tx)
        for writer in committed + buffered:
            self._edge(tx, writer)
        return True

    def _record_write(self, tx: int, writer: _Transaction, key: str) -> bool:
        """Every reader of the key that overlaps the writer gets an edge to it."""
        overlapping = []
        for other in self._readers.get(key, set()):
            t = self._serializable(other)
            if other == tx or t is None:
                continue
            if t.state == "active" or t.commit_time > writer.start:
                overlapping.append(other)
        if any(
            self._transactions[r].state == "committed" and self._live(self._transactions[r].ins)
            for r in overlapping
        ):
            writer.state = "aborted"
            return False
        for reader in overlapping:
            self._edge(reader, tx)
        return True

    def _edge(self, reader: int, writer: int) -> None:
        self._transactions[reader].outs.add(writer)
        self._transactions[writer].ins.add(reader)
