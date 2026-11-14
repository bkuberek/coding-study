"""Write-ahead logging with steal and no-force, a crash, and recovery by redo then undo.

Pages live on disk with the LSN of the last change applied to them. Changes happen in a buffer in
memory. Every change first appends a log record (its LSN, transaction, page, value before and
value after) to the log tail in memory. A commit flushes the log up to its commit record; dirty
pages are not written at commit (no-force), and a dirty page may be written before its
transaction commits (steal). The write-ahead rule: before a page goes to disk, the log is flushed
up to that page's LSN. A crash loses the buffer and the unflushed log tail.
"""


class Engine:
    def __init__(self, *, wal_rule: bool) -> None:
        self.wal_rule = wal_rule
        self.disk = {"A": (100, 0), "B": (50, 0), "C": (10, 0)}  # page -> (value, LSN)
        self.buffer: dict[str, list] = {}  # page -> [value, LSN]
        self.log: list[tuple] = []  # flushed to stable storage
        self.tail: list[tuple] = []  # still in memory
        self.next_lsn = 1

    def _append(self, *record) -> int:
        lsn = self.next_lsn
        self.next_lsn += 1
        self.tail.append((lsn, *record))
        return lsn

    def flush_log(self, upto: int) -> None:
        while self.tail and self.tail[0][0] <= upto:
            self.log.append(self.tail.pop(0))

    def update(self, txn: str, page: str, value: int) -> None:
        if page not in self.buffer:
            self.buffer[page] = list(self.disk[page])
        before = self.buffer[page][0]
        lsn = self._append(txn, "update", page, before, value)
        self.buffer[page] = [value, lsn]

    def commit(self, txn: str) -> None:
        self.flush_log(self._append(txn, "commit", None, None, None))

    def write_page(self, page: str) -> None:
        value, lsn = self.buffer[page]
        if self.wal_rule:
            self.flush_log(lsn)
        self.disk[page] = (value, lsn)

    def crash(self) -> None:
        self.buffer, self.tail = {}, []

    def recover(self) -> None:
        committed = {r[1] for r in self.log if r[2] == "commit"}
        for lsn, txn, kind, page, _before, after in self.log:  # redo: repeat history
            if kind == "update" and self.disk[page][1] < lsn:
                self.disk[page] = (after, lsn)
                print(f"  redo LSN {lsn}: {page} = {after} ({txn})")
        for lsn, txn, kind, page, before, _after in reversed(self.log):  # undo the losers
            if kind == "update" and txn not in committed:
                clr = self.next_lsn
                self.next_lsn += 1
                self.log.append((clr, txn, "compensation", page, None, before))
                self.disk[page] = (before, clr)
                print(f"  undo LSN {lsn}: {page} = {before} ({txn}), compensation LSN {clr}")

    def state(self) -> str:
        return ", ".join(f"{p}={v}" for p, (v, _) in self.disk.items())


for wal_rule in (True, False):
    print("with the write-ahead rule" if wal_rule else "without the write-ahead rule")
    db = Engine(wal_rule=wal_rule)
    db.update("T1", "A", 70)
    db.update("T2", "B", 80)
    db.update("T1", "C", 40)
    db.commit("T1")
    db.write_page("B")  # steal: T2 has not committed
    db.update("T2", "A", 60)
    db.write_page("A")  # steal again, before the log holds T2's change to A
    db.crash()
    print(f"  on disk after the crash: {db.state()}; log holds LSNs {[r[0] for r in db.log]}")
    db.recover()
    print(f"  after recovery: {db.state()}  (T1 committed A=70 and C=40; T2 never committed)")
